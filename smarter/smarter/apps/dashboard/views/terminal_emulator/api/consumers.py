"""
The web console terminal's WebSocket: a bash shell inside the server's own container.

:class:`TerminalConsumer` runs a :class:`.shell.TerminalShell` for each connection, in the server
process that accepted it, and so in whichever pod, or container, the load balancer chose. It
passes the browser's keystrokes to the shell, and the shell's output to the browser, where
xterm.js draws it. See :mod:`.messages` for the protocol.

The shell runs as the server's operating system user, with the server's environment, and so with
every credential that the server has. Only a superuser can connect, while
``smarter_settings.enable_web_console_terminal`` is set, with a single use ticket from
:class:`.tickets.TerminalTicketApiView`. A connection that fails a check is refused before the
WebSocket is accepted, and the refusal is logged.

A session ends when the shell exits, when the WebSocket closes (the page is closed or reloaded,
the connection drops, or the server restarts), after :data:`.const.TERMINAL_IDLE_TIMEOUT` seconds
without input, or after :data:`.const.TERMINAL_MAX_DURATION` seconds. Its shell, and every process
of the shell's session, is then hung up and killed. Each session's start and end are logged, with
its user, host and shell, but not what was typed, which can include credentials.
"""

import asyncio
import getpass
import socket
import time
from typing import ClassVar, Optional
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.urls import path
from pydantic import ValidationError

from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging

from ..enabled import terminal_enabled
from .const import (
    TERMINAL_IDLE_TIMEOUT,
    TERMINAL_MAX_DURATION,
    TERMINAL_MAX_SESSIONS,
    TERMINAL_WATCHDOG_INTERVAL,
    TERMINAL_WEBSOCKET_PATH,
)
from .messages import (
    TERMINAL_MAX_SIZE,
    TerminalExitMessage,
    TerminalInputMessage,
    TerminalSessionMessage,
    terminal_client_message,
)
from .shell import TerminalShell
from .tickets import redeem_ticket

logger = logging.getLogger(__name__)


def query_int(query: dict[str, list[str]], name: str, default: int) -> int:
    """
    An integer query parameter of the WebSocket's url, e.g. the terminal's initial size.

    :param query: The parsed query string.
    :param name: The parameter's name.
    :param default: The value when it is missing, not an integer, or out of range.
    :returns: The value, from 1 to :data:`.messages.TERMINAL_MAX_SIZE`.
    """
    try:
        value = int(query.get(name, [""])[0])
    except ValueError:
        return default
    return value if 1 <= value <= TERMINAL_MAX_SIZE else default


class TerminalConsumer(AsyncWebsocketConsumer, SmarterHelperMixin):
    """A bash shell for a superuser, over a WebSocket.

    See the module's docstring.
    """

    sessions: ClassVar[set["TerminalConsumer"]] = set()
    """The sessions that this server process runs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shell: Optional[TerminalShell] = None
        self.started = 0.0
        self.last_input = 0.0
        self.exit_reason: Optional[str] = None
        self.watchdog: Optional[asyncio.Task] = None
        self.closed = False

    @property
    def username(self) -> str:
        """The connected user's name, for the log."""
        return str(getattr(self.scope.get("user"), "username", "anonymous"))

    async def refuse(self, reason: str) -> None:
        """
        Refuse the connection, before accepting it: the browser sees the handshake fail.

        :param reason: Why, for the log.
        """
        logger.warning(
            "%s.connect() refused a terminal connection from %s: %s.", self.formatted_class_name, self.username, reason
        )
        await self.close()

    async def connect(self):
        """Check the user and the ticket, then accept the connection and start the shell."""
        user = self.scope.get("user")
        if not terminal_enabled():
            await self.refuse("the terminal is disabled")
            return
        if not getattr(user, "is_authenticated", False) or not getattr(user, "is_superuser", False):
            await self.refuse("not a superuser")
            return
        query = parse_qs(self.scope.get("query_string", b"").decode("utf-8", errors="replace"))
        if not await sync_to_async(redeem_ticket)(query.get("ticket", [""])[0], user.pk):
            await self.refuse("the ticket is missing, expired, used, or another user's")
            return
        if len(self.sessions) >= TERMINAL_MAX_SESSIONS:
            await self.refuse(f"this server process already runs {len(self.sessions)} sessions")
            return

        await self.accept()
        self.started = self.last_input = time.monotonic()
        self.shell = TerminalShell(
            on_output=self.send_output,
            on_exit=self.shell_exited,
            cols=query_int(query, "cols", 80),
            rows=query_int(query, "rows", 24),
        )
        try:
            await self.shell.start()
        except OSError as e:
            logger.error("%s.connect() could not start a shell for %s: %s", self.formatted_class_name, self.username, e)
            await self.send(text_data=TerminalExitMessage(reason="failed").model_dump_json())
            await self.close()
            return
        self.sessions.add(self)
        session = TerminalSessionMessage(
            hostname=socket.gethostname(),
            user=getpass.getuser(),
            command=" ".join(self.shell.command),
            pid=self.shell.pid or 0,
            idle_timeout=TERMINAL_IDLE_TIMEOUT,
            max_duration=TERMINAL_MAX_DURATION,
        )
        await self.send(text_data=session.model_dump_json())
        self.watchdog = asyncio.get_running_loop().create_task(self.watch())
        logger.info(
            "%s.connect() started a terminal session for %s on %s, as %s, shell pid %s.",
            self.formatted_class_name,
            self.username,
            session.hostname,
            session.user,
            session.pid,
        )

    async def disconnect(self, code):
        """The WebSocket closed: end the shell."""
        self.closed = True
        if self.watchdog is not None:
            self.watchdog.cancel()
        if self.shell is not None:
            await self.shell.terminate()
            logger.info(
                "%s.disconnect() ended the terminal session of %s, shell pid %s, after %d seconds (close code %s).",
                self.formatted_class_name,
                self.username,
                self.shell.pid,
                time.monotonic() - self.started,
                code,
            )
        self.sessions.discard(self)

    async def receive(self, text_data=None, bytes_data=None):
        """
        Input or a resize from the browser.

        A binary message is input. A message that is not
        valid is ignored.
        """
        if self.shell is None:
            return
        self.last_input = time.monotonic()
        if bytes_data:
            self.shell.write(bytes_data)
            return
        try:
            message = terminal_client_message.validate_json(text_data or "")
        except ValidationError as e:
            logger.warning("%s.receive() ignored a message that is not valid: %s", self.formatted_class_name, e)
            return
        if isinstance(message, TerminalInputMessage):
            self.shell.write(message.data.encode("utf-8"))
        else:
            self.shell.resize(message.cols, message.rows)

    async def send_output(self, data: bytes) -> None:
        """
        Send the shell's output to the browser.

        :param data: The output.
        """
        if not self.closed:
            await self.send(bytes_data=data)

    async def shell_exited(self, code: Optional[int]) -> None:
        """
        The shell exited: tell the browser why, and close the WebSocket.

        :param code: The shell's exit status.
        """
        if self.closed:
            return
        message = TerminalExitMessage(reason=self.exit_reason or "exited", code=code)  # type: ignore[arg-type]
        await self.send(text_data=message.model_dump_json())
        await self.close()

    async def watch(self) -> None:
        """End the session once it has been idle, or has lasted, too long."""
        while True:
            await asyncio.sleep(TERMINAL_WATCHDOG_INTERVAL)
            now = time.monotonic()
            if now - self.last_input >= TERMINAL_IDLE_TIMEOUT:
                self.exit_reason = "idle"
            elif now - self.started >= TERMINAL_MAX_DURATION:
                self.exit_reason = "expired"
            else:
                continue
            logger.info(
                "%s.watch() ending the terminal session of %s: %s.",
                self.formatted_class_name,
                self.username,
                self.exit_reason,
            )
            assert self.shell is not None
            await self.shell.terminate()
            return


urlpatterns = [
    path(TERMINAL_WEBSOCKET_PATH, TerminalConsumer.as_asgi()),  # type: ignore[arg-type]
]

__all__ = ["TerminalConsumer", "urlpatterns"]
