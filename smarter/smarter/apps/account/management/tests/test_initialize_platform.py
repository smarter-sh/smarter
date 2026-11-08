"""Test the initialize_platform management command, whose sub-commands are patched."""

from unittest.mock import ANY, patch

from django.contrib.staticfiles.management.commands import collectstatic
from django.core.management.base import CommandError
from pydantic import SecretStr

from smarter.apps.llmclient.const import (
    EXAMPLE_MANIFESTS_REPOSITORY_URL,
    STACKADEMY_REPOSITORY_URL,
)
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.initialize_platform"


def command_name(command) -> str:
    """The name of a command that call_command received, either as its name or as an instance."""
    if isinstance(command, str):
        return command
    name = command.__module__.rsplit(".", 1)[-1]
    return name


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
        # every deployment points the LLMClients' ingresses at the api's renamed Service.
        self.assertEqual(names[-2], "retarget_llmclient_ingresses")
        self.assertEqual(names[-1], "sync_infrastructure_inventory")

    def test_inventory_exit_is_logged(self):
        """Test that sync_infrastructure_inventory exiting, e.g. without a cluster, doesn't stop initialize_platform."""

        def call(name, **kwargs):
            if name == "sync_infrastructure_inventory":
                raise SystemExit(1)

        with patch(f"{MODULE}.call_command", side_effect=call), patch(f"{MODULE}.logger") as logger:
            self.run_command("initialize_platform", password="pw")
        logger.error.assert_called_once_with("Failed to sync the infrastructure inventory: %s", ANY)

    def test_retarget_failure_is_logged(self):
        """Test that retarget_llmclient_ingresses failing, e.g. a cluster error, doesn't stop initialize_platform."""

        def call(name, **kwargs):
            if name == "retarget_llmclient_ingresses":
                raise RuntimeError("cluster")

        with patch(f"{MODULE}.call_command", side_effect=call), patch(f"{MODULE}.logger") as logger:
            self.run_command("initialize_platform", password="pw")
        logger.error.assert_called_once_with("Failed to retarget the LLMClient ingresses: %s", ANY)

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

    def run_with_static_files_on_cdn(self, on_cdn: bool, call):
        """Run the command with SMARTER_STATIC_FILES_ON_CDN set, and its sub-commands patched with ``call``."""
        with (
            patch(f"{MODULE}.call_command", side_effect=call) as called,
            patch(f"{MODULE}.smarter_settings") as settings,
            patch(f"{MODULE}.mark_console_uploaded") as mark_console_uploaded,
        ):
            self.mark_console_uploaded = mark_console_uploaded
            settings.environment = SmarterEnvironments.LOCAL
            settings.root_domain = "example.com"
            settings.admin_username = "admin"
            settings.admin_password = None
            settings.static_files_on_cdn = on_cdn
            self.run_command("initialize_platform")
        return [command_name(c.args[0]) for c in called.call_args_list]

    def test_uploads_the_static_files_while_they_are_on_the_cdn(self):
        """While the static files are on the CDN, collectstatic uploads them, before the platform's other steps."""
        names = self.run_with_static_files_on_cdn(True, lambda name, **kwargs: None)
        self.assertIn("collectstatic", names)
        self.assertLess(names.index("collectstatic"), names.index("initialize_waffle"))
        # then, and only then, the console's pages point at the CDN.
        self.mark_console_uploaded.assert_called_once_with()

    def test_leaves_the_static_files_alone_while_the_server_serves_them(self):
        """Without the CDN, the image's own static files are served, and nothing is uploaded."""
        names = self.run_with_static_files_on_cdn(False, lambda name, **kwargs: None)
        self.assertNotIn("collectstatic", names)
        self.mark_console_uploaded.assert_not_called()

    def test_static_files_upload_failure_is_fatal(self):
        """A failed upload lets the remaining steps run, then fails: the pages would load missing scripts."""

        def call(command, **kwargs):
            if command_name(command) == "collectstatic":
                raise RuntimeError("bucket")

        with self.assertRaisesRegex(CommandError, "these steps failed: collectstatic"):
            self.run_with_static_files_on_cdn(True, call)
        # the pages keep loading this build from the server.
        self.mark_console_uploaded.assert_not_called()

    def test_logs_the_static_files_upload(self):
        """The upload, which runs silently for minutes, is logged before it starts and after it ends, with its counts."""

        def call(command, **kwargs):
            if command_name(command) == "collectstatic":
                command.copied_files = ["new.js", "changed.css"]
                command.symlinked_files = []
                command.unmodified_files = ["a.js", "b.js", "c.png"]

        with patch(f"{MODULE}.logger") as logger:
            self.run_with_static_files_on_cdn(True, call)
        logger.info.assert_any_call("%s.upload_static_files() uploading the static files to the CDN's bucket", ANY)
        logger.info.assert_any_call(
            "%s.upload_static_files() checked %s static files, and uploaded the %s that were new or changed, in %.0fs",
            ANY,
            5,
            2,
            ANY,
        )

    def test_collectstatic_keeps_what_it_collected(self):
        """The counts are read from the lists that Django's collectstatic keeps: a Django upgrade mustn't rename them."""
        command = collectstatic.Command()
        self.assertEqual(command.copied_files, [])
        self.assertEqual(command.symlinked_files, [])
        self.assertEqual(command.unmodified_files, [])
