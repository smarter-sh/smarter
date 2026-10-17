"""
Test smarter.apps.dashboard.views.terminal_emulator.api.consumers, the terminal's WebSocket.

The consumer runs under asgiref's ApplicationCommunicator, through :class:`Communicator`, with
the user set in its scope, as Channels' AuthMiddlewareStack sets it. (channels.testing's
WebsocketCommunicator needs daphne, which Smarter doesn't install.) Its shells are real bash processes in the container, which
each test ends. Nothing reaches the network or any infrastructure.
"""

import asyncio
import json
from typing import Optional
from unittest.mock import MagicMock, patch

from asgiref.sync import async_to_sync
from asgiref.testing import ApplicationCommunicator
from django.contrib.auth.models import AnonymousUser

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.terminal_emulator.api import consumers
from smarter.apps.dashboard.views.terminal_emulator.api.consumers import (
    TerminalConsumer,
    query_int,
)
from smarter.apps.dashboard.views.terminal_emulator.api.shell import TerminalShell
from smarter.apps.dashboard.views.terminal_emulator.api.tickets import issue_ticket
from smarter.lib.unittest.base_classes import SmarterTestBase

TIMEOUT = 10
SHELL = ("bash", "--norc", "--noprofile")


class Communicator(ApplicationCommunicator):
    """A WebSocket client of an ASGI application: the part of Channels' WebsocketCommunicator that the tests use."""

    def __init__(self, application, path: str):
        route, _, query = path.partition("?")
        scope = {"type": "websocket", "path": route, "query_string": query.encode(), "headers": [], "subprotocols": []}
        super().__init__(application, scope)

    async def connect(self, timeout: float = 1):
        await self.send_input({"type": "websocket.connect"})
        response = await self.receive_output(timeout)
        if response["type"] == "websocket.close":
            return False, response.get("code", 1000)
        return True, None

    async def send_to(self, text_data=None, bytes_data=None):
        message = {"type": "websocket.receive"}
        if text_data is not None:
            message["text"] = text_data
        if bytes_data is not None:
            message["bytes"] = bytes_data
        await self.send_input(message)

    async def disconnect(self, code: int = 1000, timeout: float = 5):
        await self.send_input({"type": "websocket.disconnect", "code": code})
        await self.wait(timeout)


class Session:
    """A WebSocket to the consumer, and what it received."""

    def __init__(self, user, ticket: Optional[str] = None, query: str = ""):
        if ticket is None:
            ticket = issue_ticket(user.pk) if getattr(user, "pk", None) else ""
        self.communicator = Communicator(TerminalConsumer.as_asgi(), f"/ws/terminal/?ticket={ticket}{query}")
        self.communicator.scope["user"] = user
        self.output = b""
        self.messages: list[dict] = []

    async def receive(self) -> dict:
        """Receive the next message: output is collected, a JSON message is returned."""
        while True:
            message = await self.communicator.receive_output(TIMEOUT)
            if message["type"] == "websocket.close":
                return {"type": "closed"}
            if message.get("bytes") is not None:
                self.output += message["bytes"]
                continue
            parsed = json.loads(message["text"])
            self.messages.append(parsed)
            return parsed

    async def wait_for(self, text: bytes) -> None:
        """Receive until the output contains the text."""
        while text not in self.output:
            message = await self.communicator.receive_output(TIMEOUT)
            if message.get("bytes") is not None:
                self.output += message["bytes"]
            elif message["type"] == "websocket.send":
                self.messages.append(json.loads(message["text"]))


class QuickShell(TerminalShell):
    """Bash without its startup files, which the tests don't need."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, command=SHELL, **kwargs)


def run(coroutine):
    return async_to_sync(coroutine)()


class TestTerminalConsumer(TestAccountMixin):
    """A superuser's shell over a WebSocket, and the connections that are refused."""

    def setUp(self):
        super().setUp()
        for patcher in (
            patch.object(consumers, "terminal_enabled", return_value=True),
            patch.object(consumers, "TerminalShell", QuickShell),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        TerminalConsumer.sessions.clear()

    def assert_refused(self, session: Session, reason: str):
        async def scenario():
            with self.assertLogs(consumers.logger.name, level="WARNING") as logs:
                connected, _ = await session.communicator.connect(TIMEOUT)
            self.assertFalse(connected)
            self.assertIn(reason, "\n".join(logs.output))

        run(scenario)

    def test_a_session(self):
        """The session message, then the shell's output for what is typed, a resize, and the exit."""

        async def scenario():
            session = Session(self.admin_user, query="&cols=100&rows=30")
            connected, _ = await session.communicator.connect(TIMEOUT)
            self.assertTrue(connected)
            hello = await session.receive()
            self.assertEqual(hello["type"], "session")
            self.assertEqual(hello["command"], "bash --norc --noprofile")
            self.assertGreater(hello["pid"], 0)
            self.assertEqual(hello["idle_timeout"], consumers.TERMINAL_IDLE_TIMEOUT)
            self.assertEqual(hello["max_duration"], consumers.TERMINAL_MAX_DURATION)
            for key in ("hostname", "user"):
                self.assertTrue(hello[key])
            self.assertEqual(len(TerminalConsumer.sessions), 1)

            await session.communicator.send_to(text_data=json.dumps({"type": "input", "data": "stty size\r"}))
            await session.wait_for(b"30 100")
            await session.communicator.send_to(text_data=json.dumps({"type": "resize", "cols": 81, "rows": 21}))
            await session.communicator.send_to(bytes_data=b"stty size\r")
            await session.wait_for(b"21 81")
            # a message that is not valid is ignored.
            with self.assertLogs(consumers.logger.name, level="WARNING"):
                await session.communicator.send_to(text_data=json.dumps({"type": "resize", "cols": 0, "rows": 5}))
                await session.communicator.send_to(text_data="not json")
                await asyncio.sleep(0.2)
            await session.communicator.send_to(text_data=json.dumps({"type": "input", "data": "exit 7\r"}))
            while (await session.receive())["type"] != "exit":
                pass
            self.assertEqual(session.messages[-1], {"type": "exit", "reason": "exited", "code": 7})
            self.assertEqual((await session.receive())["type"], "closed")
            await session.communicator.disconnect()
            self.assertEqual(TerminalConsumer.sessions, set())

        run(scenario)

    def test_closing_the_websocket_ends_the_shell(self):
        async def scenario():
            session = Session(self.admin_user)
            await session.communicator.connect(TIMEOUT)
            hello = await session.receive()
            consumer = next(iter(TerminalConsumer.sessions))
            await session.communicator.disconnect()
            await asyncio.wait_for(consumer.shell.wait_closed(), TIMEOUT)
            self.assertFalse(consumer.shell.running)
            self.assertEqual(TerminalConsumer.sessions, set())
            self.assertGreater(hello["pid"], 0)

        run(scenario)

    def test_an_idle_session_ends(self):
        async def scenario():
            with (
                patch.object(consumers, "TERMINAL_WATCHDOG_INTERVAL", 0.1),
                patch.object(consumers, "TERMINAL_IDLE_TIMEOUT", 1),
            ):
                session = Session(self.admin_user)
                await session.communicator.connect(TIMEOUT)
                while (await session.receive())["type"] != "exit":
                    pass
            self.assertEqual(session.messages[-1]["reason"], "idle")
            await session.communicator.disconnect()

        run(scenario)

    def test_a_session_expires(self):
        async def scenario():
            with (
                patch.object(consumers, "TERMINAL_WATCHDOG_INTERVAL", 0.1),
                patch.object(consumers, "TERMINAL_MAX_DURATION", 1),
            ):
                session = Session(self.admin_user)
                await session.communicator.connect(TIMEOUT)
                while (await session.receive())["type"] != "exit":
                    # input keeps it from being idle.
                    await session.communicator.send_to(text_data=json.dumps({"type": "input", "data": ""}))
            self.assertEqual(session.messages[-1]["reason"], "expired")
            await session.communicator.disconnect()

        run(scenario)

    def test_a_shell_that_cannot_start(self):
        async def scenario():
            session = Session(self.admin_user)
            with (
                patch.object(consumers.TerminalShell, "start", side_effect=OSError("no ptys")),
                self.assertLogs(consumers.logger.name, level="ERROR"),
            ):
                connected, _ = await session.communicator.connect(TIMEOUT)
                self.assertTrue(connected)
                self.assertEqual(await session.receive(), {"type": "exit", "reason": "failed", "code": None})
            self.assertEqual(TerminalConsumer.sessions, set())
            await session.communicator.disconnect()

        run(scenario)

    def test_refused_while_disabled(self):
        with patch.object(consumers, "terminal_enabled", return_value=False):
            self.assert_refused(Session(self.admin_user), "the terminal is disabled")

    def test_refused_for_a_user_who_is_not_a_superuser(self):
        self.assert_refused(Session(self.non_admin_user), "not a superuser")

    def test_refused_for_an_anonymous_user(self):
        self.assert_refused(Session(AnonymousUser()), "not a superuser")

    def test_refused_without_a_ticket(self):
        self.assert_refused(Session(self.admin_user, ticket=""), "the ticket is missing")

    def test_refused_with_another_users_ticket(self):
        self.assert_refused(Session(self.admin_user, ticket=issue_ticket(self.non_admin_user.pk)), "another user's")

    def test_refused_with_a_used_ticket(self):
        ticket = issue_ticket(self.admin_user.pk)

        async def scenario():
            session = Session(self.admin_user, ticket=ticket)
            await session.communicator.connect(TIMEOUT)
            await session.receive()
            await session.communicator.disconnect()

        run(scenario)
        self.assert_refused(Session(self.admin_user, ticket=ticket), "used")

    def test_refused_past_the_most_sessions(self):
        TerminalConsumer.sessions.update(MagicMock() for _ in range(consumers.TERMINAL_MAX_SESSIONS))
        self.addCleanup(TerminalConsumer.sessions.clear)
        self.assert_refused(Session(self.admin_user), "already runs")


class TestQueryInt(SmarterTestBase):
    """Test query_int()."""

    def test_values(self):
        self.assertEqual(query_int({"cols": ["120"]}, "cols", 80), 120)
        self.assertEqual(query_int({}, "cols", 80), 80)
        self.assertEqual(query_int({"cols": ["wide"]}, "cols", 80), 80)
        self.assertEqual(query_int({"cols": ["0"]}, "cols", 80), 80)
        self.assertEqual(query_int({"cols": ["100000"]}, "cols", 80), 80)
