"""
Test smarter.apps.dashboard.views.terminal_emulator.api.shell.

The shells are real: each test starts bash on a pseudo terminal in the container, as the server
does, and ends it. Nothing reaches the network or any infrastructure.
"""

import asyncio
import os
import re
from typing import Optional
from unittest.mock import patch

from smarter.apps.dashboard.views.terminal_emulator.api import shell as shell_module
from smarter.apps.dashboard.views.terminal_emulator.api.shell import (
    TerminalShell,
    session_pids,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

TIMEOUT = 10


class Recorder:
    """The shell's callbacks: what it wrote, and its exit status."""

    def __init__(self):
        self.output = b""
        self.exited = asyncio.Event()
        self.code: Optional[int] = None
        self.exits = 0

    async def on_output(self, data: bytes) -> None:
        self.output += data

    async def on_exit(self, code: Optional[int]) -> None:
        self.code = code
        self.exits += 1
        self.exited.set()

    async def wait_for(self, text: bytes) -> None:
        """Wait until the output contains the text."""

        async def poll():
            while text not in self.output:
                await asyncio.sleep(0.05)

        await asyncio.wait_for(poll(), TIMEOUT)


def run(coroutine):
    return asyncio.run(asyncio.wait_for(coroutine, TIMEOUT * 3))


class TestTerminalShell(SmarterTestBase):
    """A real bash on a pseudo terminal."""

    def start(self, recorder: Recorder, **kwargs) -> TerminalShell:
        return TerminalShell(on_output=recorder.on_output, on_exit=recorder.on_exit, **kwargs)

    def test_runs_commands_and_reports_the_exit_status(self):
        async def scenario():
            recorder = Recorder()
            shell = self.start(recorder, command=("bash", "--norc", "--noprofile"))
            await shell.start()
            self.assertTrue(shell.running)
            self.assertIsNotNone(shell.pid)
            shell.write(b"echo $((6 * 7)) $TERM $SMARTER_TERMINAL\r")
            await recorder.wait_for(b"42 xterm-256color true")
            shell.write(b"exit 3\r")
            await asyncio.wait_for(recorder.exited.wait(), TIMEOUT)
            await shell.wait_closed()
            self.assertEqual(recorder.code, 3)
            self.assertEqual(recorder.exits, 1)
            self.assertFalse(shell.running)
            self.assertIsNone(shell.fd)
            # writing to, resizing and ending a shell that has exited does nothing.
            shell.write(b"echo late\r")
            shell.resize(100, 30)
            await shell.terminate()

        run(scenario())

    def test_the_terminal_is_the_shells_controlling_terminal_at_its_size(self):
        async def scenario():
            recorder = Recorder()
            shell = self.start(recorder, cols=91, rows=37, command=("bash", "--norc", "--noprofile"))
            await shell.start()
            shell.write(b"stty size; tty; [ -t 0 ] && echo IS-A-TTY; echo \"SID $$ $(cut -d' ' -f6 /proc/$$/stat)\"\r")
            await recorder.wait_for(b"37 91")
            await recorder.wait_for(b"IS-A-TTY")
            shell.resize(120, 40)
            shell.write(b"stty size\r")
            await recorder.wait_for(b"40 120")
            await shell.terminate()
            await shell.wait_closed()
            self.assertIn(b"/dev/pts/", recorder.output)
            # job control works only with a controlling terminal: bash is its own session's leader.
            self.assertIn(f"SID {shell.pid} {shell.pid}".encode(), recorder.output)

        run(scenario())

    def test_terminate_kills_the_shells_session(self):
        """A background job that ignores hangups is killed too."""

        async def scenario():
            recorder = Recorder()
            shell = self.start(recorder, command=("bash", "--norc", "--noprofile"))
            await shell.start()
            shell.write(b"trap '' HUP; (trap '' HUP; sleep 600) & echo STARTED $!\r")
            await recorder.wait_for(b"STARTED ")
            await asyncio.sleep(0.2)
            pid = shell.pid
            self.assertGreater(len(session_pids(pid)), 1)
            with patch.object(shell_module, "TERMINAL_TERMINATE_GRACE", 0.5):
                await shell.terminate()
            await asyncio.wait_for(shell.wait_closed(), TIMEOUT)
            await asyncio.sleep(0.2)
            self.assertEqual(session_pids(pid), [])
            self.assertEqual(recorder.exits, 1)

        run(scenario())

    def test_without_setsid(self):
        """Without setsid, the shell still runs, in a session of its own."""

        async def scenario():
            recorder = Recorder()
            shell = self.start(recorder, command=("bash", "--norc", "--noprofile"))
            with patch.object(shell_module.shutil, "which", return_value=None):
                self.assertEqual(shell.argv(), ["bash", "--norc", "--noprofile"])
                await shell.start()
            self.assertEqual(os.getsid(shell.pid), shell.pid)
            shell.write(b"echo NO-SETSID\r")
            await recorder.wait_for(b"NO-SETSID")
            await shell.terminate()
            await shell.wait_closed()

        run(scenario())

    def test_argv_uses_setsid_with_its_controlling_terminal_option(self):
        argv = TerminalShell(on_output=None, on_exit=None).argv()  # type: ignore[arg-type]
        self.assertTrue(argv[0].endswith("setsid"))
        self.assertEqual(argv[1:], ["--ctty", "bash", "--login"])

    def test_a_shell_that_cannot_start(self):
        async def scenario():
            recorder = Recorder()
            shell = self.start(recorder, command=("/nonexistent/shell",))
            with patch.object(shell_module.shutil, "which", return_value=None), self.assertRaises(OSError):
                await shell.start()
            self.assertIsNone(shell.fd)
            self.assertFalse(shell.running)

        run(scenario())

    def test_large_output_and_input_arrive_whole_and_in_order(self):
        """Output beyond the read queue's limit pauses reading, and nothing is lost."""

        async def scenario():
            recorder = Recorder()

            async def slow_output(data: bytes) -> None:
                await asyncio.sleep(0.001)
                await recorder.on_output(data)

            shell = TerminalShell(
                on_output=slow_output, on_exit=recorder.on_exit, command=("bash", "--norc", "--noprofile")
            )
            await shell.start()
            # DO''NE is echoed as typed, and printed as DONE, once seq is done.
            shell.write(b"stty -echo; seq 1 200000; echo DO''NE\r")
            await recorder.wait_for(b"DONE\r\n")
            # each number on a line of its own. bash's bracketed paste escape may precede the first.
            numbers = re.findall(rb"(?<=[\r\n])(\d+)(?=\r\n)", recorder.output)
            self.assertEqual(numbers[0], b"1")
            self.assertEqual(numbers[-1], b"200000")
            self.assertEqual(len(numbers), 200000)
            # a paste larger than the terminal's buffer is written in parts, as the shell reads it.
            shell.write(b"cat > /dev/null\r" + b"x" * 300000 + b"\r\x04")
            shell.write(b"echo PAS''TED\r")
            await recorder.wait_for(b"PASTED\r\n")
            await shell.terminate()
            await shell.wait_closed()

        run(scenario())

    def test_an_output_callback_that_fails_does_not_end_the_session(self):
        async def scenario():
            recorder = Recorder()
            calls = []

            async def failing_output(data: bytes) -> None:
                calls.append(data)
                if len(calls) == 1:
                    raise RuntimeError("the browser went away")
                await recorder.on_output(data)

            shell = TerminalShell(
                on_output=failing_output, on_exit=recorder.on_exit, command=("bash", "--norc", "--noprofile")
            )
            await shell.start()
            await asyncio.sleep(0.3)
            shell.write(b"echo STILL-HERE\r")
            await recorder.wait_for(b"STILL-HERE")
            await shell.terminate()
            await shell.wait_closed()

        run(scenario())


class TestSessionPids(SmarterTestBase):
    """Test session_pids()."""

    def test_this_process(self):
        self.assertIn(os.getpid(), session_pids(os.getsid(0)))

    def test_no_such_session(self):
        self.assertEqual(session_pids(2**22 + 12345), [])
