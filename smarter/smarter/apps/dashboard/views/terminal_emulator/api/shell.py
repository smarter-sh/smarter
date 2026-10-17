"""
A shell on a pseudo terminal, read and written from an asyncio event loop.

:class:`TerminalShell` runs ``bash --login`` (:data:`.const.TERMINAL_SHELL`) on its own pseudo
terminal, in its own session, as the server's operating system user, in the server's environment.
It is the shell of a web console terminal session. See :mod:`.consumers`.

The shell is started with ``setsid --ctty``, so that the pseudo terminal is its controlling
terminal: then job control, Ctrl+C and full screen programs such as ``vim``, ``less`` and ``top``
work as in any terminal. Without ``setsid`` (it is in util-linux, which the Smarter image has), the
shell still runs, in its own session, but without job control.

Everything that the shell writes is read without blocking the event loop, and passed in order to
``on_output``. When the shell exits, ``on_exit`` is called once with its exit status.
:meth:`TerminalShell.terminate` hangs up the shell, and kills whatever is left of its session.
"""

import asyncio
import fcntl
import os
import pty
import shutil
import signal
import struct
import subprocess  # nosec B404: the shell's command line is a constant, and is not run by a shell.
import termios
from pathlib import Path
from typing import Awaitable, Callable, Optional

from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging

from .const import (
    TERMINAL_MAX_QUEUED_READS,
    TERMINAL_READ_SIZE,
    TERMINAL_SHELL,
    TERMINAL_TERMINATE_GRACE,
)

logger = logging.getLogger(__name__)

OutputCallback = Callable[[bytes], Awaitable[None]]
"""Called with each chunk of the shell's output, in order."""

ExitCallback = Callable[[Optional[int]], Awaitable[None]]
"""Called once, with the shell's exit status, after the shell exits."""


def session_pids(sid: int) -> list[int]:
    """
    The processes of a session: the shell, and everything it started that is still running.

    A process that started a session of its own, e.g. with ``setsid`` or as a daemon, is not
    included, nor is a zombie, which has exited, and only waits to be reaped. Reads ``/proc``, so returns an empty list where there is none, e.g. on macOS.

    :param sid: The session id, which is the shell's process id.
    :returns: The process ids.
    """
    pids = []
    for stat in Path("/proc").glob("[0-9]*/stat"):
        try:
            # the command name, in parentheses, may itself contain spaces and parentheses.
            fields = stat.read_text(encoding="utf-8", errors="replace").rpartition(")")[2].split()
        except OSError:
            continue
        # after the name: state, ppid, pgrp, session.
        if len(fields) > 3 and fields[3] == str(sid) and fields[0] != "Z":
            pids.append(int(stat.parent.name))
    return pids


class TerminalShell(SmarterHelperMixin):
    """
    A shell on a pseudo terminal.

    See the module's docstring.

    :param on_output: Called with each chunk of output.
    :param on_exit: Called once, with the exit status, after the shell exits.
    :param cols: The terminal's width, in characters.
    :param rows: The terminal's height, in lines.
    :param command: The shell's command line.
    """

    def __init__(
        self,
        on_output: OutputCallback,
        on_exit: ExitCallback,
        cols: int = 80,
        rows: int = 24,
        command: tuple[str, ...] = TERMINAL_SHELL,
    ):
        super().__init__()
        self.on_output = on_output
        self.on_exit = on_exit
        self.cols = cols
        self.rows = rows
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self.fd: Optional[int] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue()
        self._pending = b""
        self._reading = False
        self._pump: Optional[asyncio.Task] = None

    @property
    def pid(self) -> Optional[int]:
        """The shell's process id, once it has started."""
        return self.process.pid if self.process else None

    @property
    def running(self) -> bool:
        """Whether the shell has started, and has not exited."""
        return self.process is not None and self.process.poll() is None

    @staticmethod
    def environment() -> dict[str, str]:
        """
        The shell's environment: the server's, for a color terminal.

        :returns: The environment variables.
        """
        return {
            **os.environ,
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "SMARTER_TERMINAL": "true",
        }

    def argv(self) -> list[str]:
        """
        The command line that starts the shell: under ``setsid --ctty`` where there is one.

        :returns: The command line.
        """
        setsid = shutil.which("setsid")
        return [setsid, "--ctty", *self.command] if setsid else list(self.command)

    async def start(self) -> None:
        """
        Start the shell, and begin reading its output.

        :raises OSError: If the pseudo terminal cannot be opened, or the shell cannot be started.
        """
        self._loop = asyncio.get_running_loop()
        fd, terminal = pty.openpty()
        try:
            self.set_size(fd, self.cols, self.rows)
            argv = self.argv()
            self.process = subprocess.Popen(  # nosec B603: a constant command line, without a shell.
                argv,
                stdin=terminal,
                stdout=terminal,
                stderr=terminal,
                cwd=Path.home(),
                env=self.environment(),
                close_fds=True,
                # setsid --ctty makes its own session. Without it, Popen does.
                start_new_session=argv[0] in self.command,
            )
        except OSError:
            os.close(fd)
            raise
        finally:
            os.close(terminal)
        self.fd = fd
        os.set_blocking(fd, False)
        self._resume_reading()
        self._pump = self._loop.create_task(self._send_output())
        logger.debug("%s.start() started %s, pid %s.", self.formatted_class_name, argv, self.pid)

    @staticmethod
    def set_size(fd: int, cols: int, rows: int) -> None:
        """
        Set a terminal's size. The shell, and the program in its foreground, get a ``SIGWINCH``.

        :param fd: The pseudo terminal.
        :param cols: The width, in characters.
        :param rows: The height, in lines.
        """
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    def resize(self, cols: int, rows: int) -> None:
        """
        Resize the shell's terminal.

        :param cols: The width, in characters.
        :param rows: The height, in lines.
        """
        self.cols, self.rows = cols, rows
        if self.fd is not None:
            self.set_size(self.fd, cols, rows)

    def write(self, data: bytes) -> None:
        """
        Write input to the shell, as if it were typed.

        Input that the terminal cannot take yet is
        written as soon as it can.

        :param data: The input.
        """
        if self.fd is None or not data:
            return
        self._pending += data
        self._flush()

    def _flush(self) -> None:
        if self.fd is None:
            return
        try:
            written = os.write(self.fd, self._pending)
        except BlockingIOError:
            written = 0
        except OSError as e:
            # the shell exited: its output's end, which is being read, ends the session.
            logger.debug("%s._flush() could not write to the terminal: %s", self.formatted_class_name, e)
            self._pending = b""
            return
        self._pending = self._pending[written:]
        assert self._loop is not None
        if self._pending:
            self._loop.add_writer(self.fd, self._flush)
        else:
            self._loop.remove_writer(self.fd)

    def _resume_reading(self) -> None:
        if self.fd is not None and not self._reading:
            assert self._loop is not None
            self._loop.add_reader(self.fd, self._read)
            self._reading = True

    def _pause_reading(self) -> None:
        if self.fd is not None and self._reading:
            assert self._loop is not None
            self._loop.remove_reader(self.fd)
            self._reading = False

    def _read(self) -> None:
        assert self.fd is not None
        try:
            data = os.read(self.fd, TERMINAL_READ_SIZE)
        except BlockingIOError:
            return
        except OSError:
            # EIO: the shell, and everything else that had the terminal open, exited.
            data = b""
        if not data:
            self._pause_reading()
            self._queue.put_nowait(None)
            return
        self._queue.put_nowait(data)
        # don't read faster than the browser receives, e.g. from `yes`.
        if self._queue.qsize() >= TERMINAL_MAX_QUEUED_READS:
            self._pause_reading()

    async def _send_output(self) -> None:
        """Pass the output to ``on_output`` in order, then, when it ends, finish."""
        while True:
            data = await self._queue.get()
            if data is None:
                break
            try:
                await self.on_output(data)
            # pylint: disable=broad-except
            except Exception as e:
                logger.warning("%s._send_output() could not send output: %s", self.formatted_class_name, e)
            if self._queue.qsize() < TERMINAL_MAX_QUEUED_READS // 2:
                self._resume_reading()
        await self._finish()

    async def _finish(self) -> None:
        assert self.process is not None and self._loop is not None
        code = await self._loop.run_in_executor(None, self.process.wait)
        if self.fd is not None:
            self._loop.remove_writer(self.fd)
            os.close(self.fd)
            self.fd = None
        logger.debug("%s._finish() pid %s exited with status %s.", self.formatted_class_name, self.pid, code)
        await self.on_exit(code)

    def _signal(self, sig: int) -> None:
        """Send a signal to every process of the shell's session."""
        if self.pid is None:
            return
        pids = set(session_pids(self.pid))
        # once the shell is reaped, its process id may be reused: signal it only while it runs.
        if self.running:
            pids.add(self.pid)
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass

    async def terminate(self) -> None:
        """
        End the shell: hang it up, as when a terminal is closed, then, after.

        :data:`.const.TERMINAL_TERMINATE_GRACE` seconds, kill what is left of its session.

        The shell's exit then ends its output, and ``on_exit`` is called. Does nothing if the shell
        is not running.
        """
        if not self.running:
            return
        assert self.process is not None and self._loop is not None
        self._signal(signal.SIGHUP)
        self._signal(signal.SIGCONT)
        try:
            await asyncio.wait_for(
                self._loop.run_in_executor(None, self.process.wait), timeout=TERMINAL_TERMINATE_GRACE
            )
        except asyncio.TimeoutError:
            logger.warning(
                "%s.terminate() pid %s did not hang up within %s seconds, and is killed.",
                self.formatted_class_name,
                self.pid,
                TERMINAL_TERMINATE_GRACE,
            )
            self._signal(signal.SIGKILL)
        # e.g. a background job that ignores SIGHUP, which keeps the terminal open.
        self._signal(signal.SIGKILL)

    async def wait_closed(self) -> None:
        """Wait until the shell's output has been passed on, and ``on_exit`` has been called."""
        if self._pump is not None:
            await self._pump
