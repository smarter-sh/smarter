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

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.management.commands.deploy_builtin_llmclients import Command
from smarter.apps.plugin.models import PluginMeta
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
