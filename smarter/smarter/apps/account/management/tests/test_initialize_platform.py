"""Test the initialize_platform management command, whose sub-commands are patched."""

from unittest.mock import patch

from smarter.common.const import SmarterEnvironments

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.initialize_platform"


class TestInitializePlatform(CommandTestBase):
    def test_runs_each_initialization_command(self):
        with patch(f"{MODULE}.call_command") as call:
            self.run_command("initialize_platform", username="admin", email="admin@example.com", password="pw")
        names = [c.args[0] for c in call.call_args_list]
        self.assertEqual(names[:3], ["create_smarter_admin", "create_user", "create_user"])
        self.assertIn("initialize_waffle", names)
        self.assertIn("verify_dns_configuration", names)

    def test_failures_are_logged(self):
        """Test that a failure of an optional initialization command doesn't stop the others."""

        def call(name, **kwargs):
            if name not in ("create_smarter_admin", "create_user"):
                raise RuntimeError(name)

        with patch(f"{MODULE}.call_command", side_effect=call), patch(f"{MODULE}.logger") as logger:
            self.run_command("initialize_platform", password="pw")
        self.assertGreaterEqual(logger.error.call_count, 10)

    def test_defaults(self):
        with patch(f"{MODULE}.call_command") as call, patch(f"{MODULE}.smarter_settings") as settings:
            settings.environment = SmarterEnvironments.LOCAL
            settings.root_domain = "example.com"
            self.run_command("initialize_platform")
        self.assertEqual(
            call.call_args_list[0].kwargs, {"username": "admin", "password": "smarter", "email": "admin@example.com"}
        )

    def test_password_required_outside_local(self):
        with patch(f"{MODULE}.call_command") as call, patch(f"{MODULE}.smarter_settings") as settings:
            settings.environment = SmarterEnvironments.PROD
            self.run_command("initialize_platform")
        call.assert_not_called()
