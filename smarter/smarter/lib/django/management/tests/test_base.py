"""Test :class:`smarter.lib.django.management.base.SmarterCommand`."""

from io import StringIO
from unittest.mock import patch

from django.core.management.base import CommandError, OutputWrapper

from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.lib.django.management.base"


class TestSmarterCommand(SmarterTestBase):
    """Test the base command's logging helpers, its parser and its handle()."""

    def setUp(self):
        super().setUp()
        self.command = SmarterCommand()

    def test_handle_begin_and_success(self):
        with patch(f"{MODULE}.logger") as logger:
            self.command.handle_begin()
            self.command.handle_completed_success()
            self.command.handle_completed_success("all done")
        messages = [call.args for call in logger.info.call_args_list]
        self.assertIn(("%s", "all done"), messages)
        self.assertIn(("%s completed successfully.", self.command.__module__), messages)

    def test_handle_completed_failure(self):
        """Test that a failure with an error exits with status 1, and a failure without one doesn't exit."""
        with patch(f"{MODULE}.logger") as logger:
            self.command.handle_completed_failure(msg="no error")
            with self.assertRaises(SystemExit) as context:
                self.command.handle_completed_failure(err=ValueError("bad"), msg="an error")
        self.assertEqual(context.exception.code, 1)
        messages = [call.args for call in logger.error.call_args_list]
        self.assertIn(("%s", "an error"), messages)
        self.assertIn(("%s", f"{self.command.__module__} failed."), messages)
        self.assertIn(("%s", f"{self.command.__module__} failed with error: bad"), messages)

    def test_parser(self):
        parser = self.command.create_parser("manage.py", "a_command")
        self.assertTrue(parser.parse_args(["--settings_output"]).settings_output)
        self.assertFalse(parser.parse_args([]).settings_output)

    def test_handle(self):
        with self.assertRaises(NotImplementedError):
            self.command.handle()

    def test_run_from_argv_reports_an_unexpected_error_without_a_stack_trace(self):
        """Test that an unexpected error prints one line, and exits with status 1."""
        err = StringIO()
        self.command.stderr = OutputWrapper(err)
        with patch.object(SmarterCommand, "handle", side_effect=ValueError("bad value")):
            with self.assertRaises(SystemExit) as context:
                self.command.run_from_argv(["manage.py", "a_command"])
        self.assertEqual(context.exception.code, 1)
        self.assertIn("ValueError: bad value", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_run_from_argv_with_traceback_raises(self):
        with patch.object(SmarterCommand, "handle", side_effect=ValueError("bad value")):
            with self.assertRaises(ValueError):
                self.command.run_from_argv(["manage.py", "a_command", "--traceback"])

    def test_run_from_argv_leaves_command_errors_to_django(self):
        """Test that a CommandError is still Django's to print, as one line with status 1."""
        err = StringIO()
        self.command.stderr = OutputWrapper(err)
        with patch.object(SmarterCommand, "handle", side_effect=CommandError("no such thing")):
            with self.assertRaises(SystemExit) as context:
                self.command.run_from_argv(["manage.py", "a_command"])
        self.assertEqual(context.exception.code, 1)
        self.assertIn("CommandError: no such thing", err.getvalue())
