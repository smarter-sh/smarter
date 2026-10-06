"""
Test :mod:`smarter.apps.llmclient.management.commands.deploy_builtin_llmclients`.

A built-in manifest that fails to apply must be rolled back entirely, and must not prevent
the other built-in manifests from being applied.
"""

import copy
import os
import tempfile
from io import StringIO
from unittest.mock import patch

import yaml
from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.management.commands.deploy_builtin_llmclients import Command
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.plugin.models import PluginMeta
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.loader import SAMLoader

MODULE = "smarter.apps.llmclient.management.commands.deploy_builtin_llmclients"
HERE = os.path.abspath(os.path.dirname(__file__))
SMARTER_PROJECT_WEBSEARCH_PATH = os.path.join(HERE, "..", "data", "plugins", "plugin-smarter-websearch.yaml")


class TestDeployBuiltinLLMClients(TestAccountMixin):
    """Test that deploy_builtin_llmclients applies each built-in manifest on its own."""

    def setUp(self):
        super().setUp()
        self.command = Command(stdout=StringIO(), stderr=StringIO())
        self.command.user_profile = self.user_profile

    def write_manifest(self, manifest: dict) -> str:
        """Write a manifest to a temporary yaml file, and return its path."""
        directory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "manifest.yaml")
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(manifest, f)
        return path

    def test_failed_plugin_is_rolled_back(self):
        """Test that a plugin whose Secret does not exist fails, and leaves no PluginMeta behind."""
        name = f"test_deploy_builtin_{self.hash_suffix}"
        self.addCleanup(PluginMeta.objects.filter(name=name).delete)
        manifest = copy.deepcopy(get_readonly_yaml_file(SMARTER_PROJECT_WEBSEARCH_PATH))
        manifest["metadata"]["name"] = name
        manifest["spec"]["websearchData"]["search"]["apiKey"] = f"no_such_secret_{self.hash_suffix}"

        self.assertFalse(self.command.create_plugin(self.write_manifest(manifest)))
        self.assertFalse(PluginMeta.objects.filter(name=name).exists())
        self.assertIn("SmarterWebsearchPluginError", self.command.stderr.getvalue())  # type: ignore[union-attr]

    def test_apply_manifest_reports_failures(self):
        """Test that any exception, or exit, of apply_manifest is reported rather than raised."""
        manifest = SAMLoader(file_path=SMARTER_PROJECT_WEBSEARCH_PATH)
        for error in (RuntimeError("broker error"), SystemExit(1)):
            with self.subTest(error=type(error).__name__), patch(f"{MODULE}.call_command", side_effect=error):
                self.assertFalse(self.command.apply_manifest(manifest, "a.yaml"))
        with patch(f"{MODULE}.call_command") as call_command:
            self.assertTrue(self.command.apply_manifest(manifest, "a.yaml"))
        call_command.assert_called_once()

    def test_failed_llmclient_is_not_deployed(self):
        """Test that an LLMClient whose manifest fails to apply is not deployed."""
        with patch.object(Command, "apply_manifest", return_value=False):
            path = os.path.join(HERE, "..", "data", "llm-clients", "llmclient-smarter.yaml")
            self.assertFalse(self.command.create_and_deploy_llmclient(path))

    def test_url(self):
        """Test that the url is required, and validated."""
        with self.assertRaises(SmarterValueError):
            _ = self.command.url
        self.command.url = "https://example.com/"
        self.assertEqual(self.command.url, "https://example.com/")

    def test_user_profile_is_required(self):
        """Test that deleting, or creating, a plugin or llmclient requires a user profile."""
        command = Command(stdout=StringIO(), stderr=StringIO())
        command.user_profile = None
        for method, arg in (
            (command.delete_llmclient, "name"),
            (command.create_plugin, "a.yaml"),
            (command.create_and_deploy_llmclient, "a.yaml"),
        ):
            with self.subTest(method=method.__name__), self.assertRaises(SmarterValueError):
                method(arg)

    def test_delete_llmclient(self):
        """Test that an llmclient is deleted by name, and that an unknown name is ignored."""
        name = f"test_deploy_builtin_delete_{self.hash_suffix}"
        LLMClient.objects.create(name=name, user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(name=name).delete)
        with patch("smarter.apps.llmclient.receivers.delete_default_api"):
            self.command.delete_llmclient(name)
            self.command.delete_llmclient(f"no_such_llmclient_{self.hash_suffix}")
        self.assertFalse(LLMClient.objects.filter(name=name).exists())
        self.assertIn(name, self.command.stdout.getvalue())  # type: ignore[union-attr]

    def test_applied_llmclient_not_found(self):
        """Test that an LLMClient that is not found after its manifest is applied is not deployed."""
        path = os.path.join(HERE, "..", "data", "llm-clients", "llmclient-smarter.yaml")
        with patch.object(Command, "apply_manifest", return_value=True):
            self.assertFalse(self.command.create_and_deploy_llmclient(path))
        self.assertIn("Error occurred while deploying llmclient", self.command.stderr.getvalue())  # type: ignore[union-attr]

    def test_handle(self):
        """Test that the command creates each built-in plugin, then creates and deploys each built-in llmclient."""
        with (
            patch(f"{MODULE}.glob.glob", side_effect=[["plugin.yaml"], ["llmclient.yaml"]]),
            patch.object(Command, "create_plugin", return_value=True) as create_plugin,
            patch.object(Command, "create_and_deploy_llmclient", return_value=True) as create_and_deploy_llmclient,
        ):
            call_command("deploy_builtin_llmclients", account_number=self.account.account_number, stdout=StringIO())
        create_plugin.assert_called_once_with(filespec="plugin.yaml")
        create_and_deploy_llmclient.assert_called_once_with(filespec="llmclient.yaml")

    def test_handle_requires_account_number(self):
        with self.assertRaises(SmarterValueError):
            call_command("deploy_builtin_llmclients", account_number="", stdout=StringIO(), stderr=StringIO())
