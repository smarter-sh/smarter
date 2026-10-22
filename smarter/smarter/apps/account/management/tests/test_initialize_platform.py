"""Test the initialize_platform management command, whose sub-commands are patched."""

from unittest.mock import ANY, patch

from django.core.management.base import CommandError
from pydantic import SecretStr

from smarter.apps.llmclient.const import STACKADEMY_REPOSITORY_URL
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.initialize_platform"


class TestInitializePlatform(CommandTestBase):
    def test_runs_each_initialization_command(self):
        with patch(f"{MODULE}.call_command") as call:
            self.run_command("initialize_platform", username="admin", email="admin@example.com", password="pw")
        names = [c.args[0] for c in call.call_args_list]
        self.assertEqual(names[:3], ["create_smarter_admin", "create_user", "create_user"])
        self.assertIn("initialize_waffle", names)
        self.assertIn("add_example_custom_domains", names)
        self.assertIn("index_smarter_project", names)
        self.assertEqual(call.call_args_list[names.index("index_smarter_project")].kwargs, {"queue": True})
        # the examples, then the Stackademy project, from GitHub, then its LLMClients' verification.
        examples = [
            "add_example_tools",
            "add_example_llmclients",
            "load_from_github",
            "verify_stackademy",
        ]
        self.assertEqual([name for name in names if name in examples], examples)
        for name in examples[:2]:
            self.assertEqual(call.call_args_list[names.index(name)].kwargs, {"username": "admin"})
        # the tests run in the local environment, where nothing is deployed.
        self.assertEqual(
            call.call_args_list[names.index("load_from_github")].kwargs,
            {
                "url": STACKADEMY_REPOSITORY_URL,
                "account_number": SMARTER_ACCOUNT_NUMBER,
                "username": "admin",
                "deploy": False,
            },
        )
        for dependency in ("initialize_providers", "add_example_extensions", "add_example_mcpclients"):
            self.assertLess(names.index(dependency), names.index("add_example_llmclients"))
        self.assertLess(names.index("initialize_providers"), names.index("load_from_github"))
        self.assertNotIn("deploy_example_llmclients", names)
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
            with self.assertRaises(CommandError):
                self.run_command("initialize_platform", password="pw")
        self.assertGreaterEqual(logger.error.call_count, 10)

    def test_extension_failure_is_fatal(self):
        """Test that a failure of add_example_extensions lets the remaining steps run, then fails with a CommandError, which exits with code 1."""

        def call(name, **kwargs):
            if name == "add_example_extensions":
                raise SystemExit(1)

        with patch(f"{MODULE}.call_command", side_effect=call) as called:
            with self.assertRaisesRegex(CommandError, "these steps failed: add_example_extensions") as raised:
                self.run_command("initialize_platform", password="pw")
        self.assertEqual(raised.exception.returncode, 1)
        self.assertEqual(called.call_args_list[-1].args[0], "sync_infrastructure_inventory")

    def test_defaults(self):
        with patch(f"{MODULE}.call_command") as call, patch(f"{MODULE}.smarter_settings") as settings:
            settings.environment = SmarterEnvironments.LOCAL
            settings.root_domain = "example.com"
            settings.admin_username = "admin"
            settings.admin_password = None
            self.run_command("initialize_platform")
        self.assertEqual(
            call.call_args_list[0].kwargs, {"username": "admin", "password": "smarter", "email": "admin@example.com"}
        )

    def test_credentials_from_settings(self):
        """Test that the admin credentials come from smarter_settings, so the init job passes none on its command line."""
        with patch(f"{MODULE}.call_command") as call, patch(f"{MODULE}.smarter_settings") as settings:
            settings.environment = SmarterEnvironments.PROD
            settings.root_domain = "example.com"
            settings.admin_username = "platform-admin"
            settings.admin_password = SecretStr("from-env")
            self.run_command("initialize_platform")
        self.assertEqual(
            call.call_args_list[0].kwargs,
            {"username": "platform-admin", "password": "from-env", "email": "platform-admin@example.com"},
        )

    def test_arguments_override_settings(self):
        with patch(f"{MODULE}.call_command") as call, patch(f"{MODULE}.smarter_settings") as settings:
            settings.environment = SmarterEnvironments.PROD
            settings.root_domain = "example.com"
            settings.admin_username = "platform-admin"
            settings.admin_password = SecretStr("from-env")
            self.run_command("initialize_platform", username="cli-admin", password="cli-pw")
        self.assertEqual(call.call_args_list[0].kwargs["username"], "cli-admin")
        self.assertEqual(call.call_args_list[0].kwargs["password"], "cli-pw")

    def test_password_required_outside_local(self):
        """Test that a missing password outside the local environment fails, so the init job fails."""
        with patch(f"{MODULE}.call_command") as call, patch(f"{MODULE}.smarter_settings") as settings:
            settings.environment = SmarterEnvironments.PROD
            settings.admin_username = "admin"
            settings.admin_password = None
            with self.assertRaisesRegex(CommandError, "SMARTER_ADMIN_PASSWORD"):
                self.run_command("initialize_platform")
        call.assert_not_called()

    def test_deploys_outside_local(self):
        """Test that outside the local environment the example and Stackademy LLMClients are deployed."""
        with patch(f"{MODULE}.call_command") as call, patch(f"{MODULE}.smarter_settings") as settings:
            settings.environment = SmarterEnvironments.PROD
            settings.root_domain = "example.com"
            settings.admin_username = "admin"
            settings.admin_password = SecretStr("pw")
            self.run_command("initialize_platform")
        names = [c.args[0] for c in call.call_args_list]
        self.assertEqual(
            call.call_args_list[names.index("deploy_example_llmclients")].kwargs,
            {"account_number": SMARTER_ACCOUNT_NUMBER},
        )
        self.assertLess(names.index("add_example_llmclients"), names.index("deploy_example_llmclients"))
        self.assertTrue(call.call_args_list[names.index("load_from_github")].kwargs["deploy"])
        self.assertLess(names.index("load_from_github"), names.index("verify_stackademy"))

    def test_deploy_failures_are_fatal(self):
        """Test that a failed deploy, or a failed Stackademy load, fails initialize_platform once every step has run."""

        def call(name, **kwargs):
            if name in ("deploy_example_llmclients", "load_from_github"):
                raise SystemExit(1)

        with (
            patch(f"{MODULE}.call_command", side_effect=call) as called,
            patch(f"{MODULE}.smarter_settings") as settings,
        ):
            settings.environment = SmarterEnvironments.PROD
            settings.root_domain = "example.com"
            settings.admin_username = "admin"
            settings.admin_password = SecretStr("pw")
            with self.assertRaisesRegex(CommandError, "deploy_example_llmclients, load_from_github"):
                self.run_command("initialize_platform")
        self.assertEqual(called.call_args_list[-1].args[0], "sync_infrastructure_inventory")
