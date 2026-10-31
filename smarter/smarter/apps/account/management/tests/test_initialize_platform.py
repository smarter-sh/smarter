"""Test the initialize_platform management command, whose sub-commands are patched."""

from unittest.mock import ANY, patch

from django.core.management.base import CommandError
from pydantic import SecretStr

from smarter.apps.llmclient.const import (
    EXAMPLE_MANIFESTS_REPOSITORY_URL,
    STACKADEMY_REPOSITORY_URL,
)
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.initialize_platform"


class TestInitializePlatform(CommandTestBase):
    def loads(self, call) -> dict[str, dict]:
        """The keyword arguments of each load_from_github, by repository url."""
        return {c.kwargs["url"]: c.kwargs for c in call.call_args_list if c.args[0] == "load_from_github"}

    def test_runs_each_initialization_command(self):
        with patch(f"{MODULE}.call_command") as call:
            self.run_command("initialize_platform", username="admin", email="admin@example.com", password="pw")
        names = [c.args[0] for c in call.call_args_list]
        self.assertEqual(names[:3], ["create_smarter_admin", "create_user", "create_user"])
        self.assertIn("initialize_waffle", names)
        self.assertIn("index_smarter_project", names)
        self.assertEqual(call.call_args_list[names.index("index_smarter_project")].kwargs, {"queue": True})
        self.assertFalse([name for name in names if name.startswith(("add_example_", "deploy_example_"))])
        # the example manifests, then the Stackademy project, from GitHub, then its LLMClients' verification.
        urls = [c.kwargs["url"] for c in call.call_args_list if c.args[0] == "load_from_github"]
        self.assertEqual(urls, [EXAMPLE_MANIFESTS_REPOSITORY_URL, STACKADEMY_REPOSITORY_URL])
        # the tests run in the local environment, where nothing is deployed.
        for url in urls:
            expected = {
                "url": url,
                "account_number": SMARTER_ACCOUNT_NUMBER,
                "username": "admin",
                "deploy": False,
                "run_scripts": True,
            }
            if url == EXAMPLE_MANIFESTS_REPOSITORY_URL:
                # the examples that need a Secret of a third-party service wait for it. Stackademy brings its own.
                expected["skip_missing_references"] = True
            self.assertEqual(self.loads(call)[url], expected)
        first_load = names.index("load_from_github")
        for dependency in ("initialize_providers", "install_official_extensions", "initialize_vectorstore_providers"):
            self.assertLess(names.index(dependency), first_load)
        self.assertLess(len(names) - 1 - names[::-1].index("load_from_github"), names.index("verify_stackademy"))
        # the retired examples are deleted after the example manifests are loaded, for their owner.
        retired = names.index("delete_retired_examples")
        self.assertEqual(retired, first_load + 1)
        self.assertEqual(call.call_args_list[retired].kwargs, {"username": "admin"})
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
        """Test that a failure of install_official_extensions lets the remaining steps run, then fails with a CommandError, which exits with code 1."""

        def call(name, **kwargs):
            if name == "install_official_extensions":
                raise SystemExit(1)

        with patch(f"{MODULE}.call_command", side_effect=call) as called:
            with self.assertRaisesRegex(CommandError, "these steps failed: install_official_extensions") as raised:
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
        loads = self.loads(call)
        self.assertTrue(loads[EXAMPLE_MANIFESTS_REPOSITORY_URL]["deploy"])
        self.assertTrue(loads[STACKADEMY_REPOSITORY_URL]["deploy"])

    def test_stackademy_failure_is_fatal(self):
        """Test that a failed Stackademy load fails initialize_platform once every step has run, and a failed example load doesn't."""

        def call(name, **kwargs):
            if name == "load_from_github":
                raise SystemExit(1)

        with (
            patch(f"{MODULE}.call_command", side_effect=call) as called,
            patch(f"{MODULE}.smarter_settings") as settings,
            patch(f"{MODULE}.logger") as logger,
        ):
            settings.environment = SmarterEnvironments.PROD
            settings.root_domain = "example.com"
            settings.admin_username = "admin"
            settings.admin_password = SecretStr("pw")
            with self.assertRaisesRegex(CommandError, "these steps failed: load_from_github$"):
                self.run_command("initialize_platform")
        self.assertEqual(called.call_args_list[-1].args[0], "sync_infrastructure_inventory")
        logger.error.assert_any_call(
            "Failed to load the example manifests from %s: %s", EXAMPLE_MANIFESTS_REPOSITORY_URL, ANY
        )
