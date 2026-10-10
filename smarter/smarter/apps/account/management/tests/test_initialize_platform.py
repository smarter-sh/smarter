"""Test the initialize_platform management command, whose sub-commands are patched."""

from unittest.mock import ANY, patch

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
        self.assertIn("add_builtin_custom_domains", names)
        self.assertIn("add_plugin_examples", names)
        self.assertIn("create_stackademy", names)
        self.assertLess(names.index("initialize_providers"), names.index("create_stackademy"))
        self.assertIn("verify_dns_configuration", names)
        self.assertEqual(names[-1], "sync_infrastructure_inventory")

    def test_inventory_exit_is_logged(self):
        """Test that sync_infrastructure_inventory exiting, e.g. without a cluster, doesn't stop initialize_platform."""

        def call(name, **kwargs):
            if name == "sync_infrastructure_inventory":
                raise SystemExit(1)

        with patch(f"{MODULE}.call_command", side_effect=call), patch(f"{MODULE}.logger") as logger:
            self.run_command("initialize_platform", password="pw")
        logger.error.assert_called_once_with("Failed to sync the infrastructure inventory: %s", ANY)

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
