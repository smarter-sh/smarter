"""Test :class:`smarter.lib.django.management.base.SmarterCommand`."""

from unittest.mock import patch

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
