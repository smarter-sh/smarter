"""
Test the error and fallback branches of the load_from_github management command.

The repository is a local temporary folder in place of a GitHub clone, so nothing is fetched.
"""

import os
import shutil
import subprocess
import tempfile
from unittest.mock import MagicMock, PropertyMock, patch

from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.management.commands.load_from_github import Command
from smarter.common.exceptions import SmarterValueError

MODULE = "smarter.apps.llmclient.management.commands.load_from_github"
URL = "https://github.com/smarter-sh/no-such-repo"


class TestLoadFromGithub(TestAccountMixin):
    """Test load_from_github against a local repository folder."""

    def command(self, user_profile=None) -> Command:
        command = Command()
        command.url = URL
        command.user_profile = user_profile if user_profile is not None else MagicMock()
        command.user = MagicMock(username="someone")
        command.account = MagicMock(account_number="0000-0000-0000")
        return command

    def repo(self, files: list[str]) -> str:
        """A local repository folder holding the given (empty) files."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for name in files:
            path = os.path.join(root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("apiVersion: smarter.sh/v1\n")
        return root

    def use_repo(self, root: str):
        """Make the command read ``root`` in place of cloning."""
        for patcher in (
            patch.object(Command, "local_path", new_callable=PropertyMock, return_value=root),
            patch.object(Command, "clone_repo"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_url_is_required(self):
        with self.assertRaises(SmarterValueError):
            _ = Command().url

    def test_failed_clone_raises(self):
        command = self.command()
        with patch(f"{MODULE}.subprocess.call", return_value=1), patch.object(Command, "delete_repo"):
            with self.assertRaises(subprocess.CalledProcessError):
                command.clone_repo()

    def test_delete_repo(self):
        command = self.command()
        with patch(f"{MODULE}.os.path.exists", return_value=True):
            with patch(f"{MODULE}.subprocess.call", return_value=0) as call:
                command.delete_repo()
            call.assert_called_once()
            with patch(f"{MODULE}.subprocess.call", return_value=1):
                with self.assertRaises(subprocess.CalledProcessError):
                    command.delete_repo()

    def test_user_profile_is_required(self):
        command = self.command()
        command.user_profile = None
        for method in (command.process_repo_v1, command.process_repo_v2):
            with self.subTest(method=method.__name__):
                with self.assertRaises(SmarterValueError):
                    method()
        with self.assertRaises(SmarterValueError):
            command.load_plugin(filespec="plugin.yaml")

    def test_load_plugin_exits_when_the_loader_is_not_ready(self):
        with patch(f"{MODULE}.SAMLoader", return_value=MagicMock(ready=False)):
            with self.assertRaises(SystemExit):
                self.command().load_plugin(filespec="plugin.yaml")

    def test_v2_applies_plugins_then_llmclients(self):
        self.use_repo(self.repo(["plugins/p.yaml", "llmclients/c.yml", "llmclients/readme.md"]))
        with patch(f"{MODULE}.apply_manifest") as apply_manifest:
            self.command().process_repo_v2()
        applied = [os.path.basename(call.kwargs["filespec"]) for call in apply_manifest.call_args_list]
        self.assertEqual(applied, ["p.yaml", "c.yml"])

    def test_v1_skips_invalid_folders_and_plugins_that_do_not_load(self):
        self.use_repo(self.repo(["not_a_host/p.yaml", "demo/p.yaml", "empty/readme.md"]))
        llmclient_model = MagicMock()
        llmclient = MagicMock()
        llmclient_model.objects.get_or_create.return_value = (llmclient, True)
        with patch(f"{MODULE}.LLMClient", llmclient_model), patch(f"{MODULE}.LLMClientPlugin") as llmclient_plugin:
            with patch.object(Command, "load_plugin", return_value=None):
                self.command().process_repo_v1()
        llmclient_model.objects.get_or_create.assert_called_once()
        self.assertEqual(llmclient_model.objects.get_or_create.call_args.kwargs["name"], "demo")
        llmclient_plugin.objects.get_or_create.assert_not_called()
        llmclient.save.assert_called_once_with(asynchronous=True)

    def test_v1_plugin_failure_is_raised(self):
        self.use_repo(self.repo(["demo/p.yaml"]))
        with patch(f"{MODULE}.LLMClient") as llmclient_model:
            llmclient_model.objects.get_or_create.return_value = (MagicMock(), True)
            with patch.object(Command, "load_plugin", side_effect=RuntimeError("bad plugin")):
                with self.assertRaises(RuntimeError):
                    self.command().process_repo_v1()

    def test_account_or_username_is_required(self):
        with self.assertRaises(SmarterValueError):
            call_command("load_from_github", "--url", URL)

    def test_account_admin_is_the_default_user_and_failures_exit(self):
        with patch.object(Command, "process_repo_v1", side_effect=RuntimeError("boom")) as process:
            with self.assertRaises(SystemExit):
                call_command("load_from_github", "--url", URL, "--account_number", self.account.account_number)
        process.assert_called_once()
