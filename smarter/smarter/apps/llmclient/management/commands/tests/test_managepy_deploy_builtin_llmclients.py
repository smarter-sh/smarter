"""
Test :mod:`smarter.apps.llmclient.management.commands.deploy_builtin_llmclients`.

A built-in manifest that fails to apply must be rolled back entirely, and must not prevent
the other built-in manifests from being applied.
"""

import copy
import glob
import os
import tempfile
from io import StringIO
from unittest.mock import patch

import yaml
from django.core.management import call_command
from django.core.management.base import CommandError

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmclient.management.commands.deploy_builtin_llmclients import Command
from smarter.apps.llmclient.manifest.models.llmclient.model import SAMLLMClient
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmtool.models import PluginMeta
from smarter.common.const import PROJECT_ROOT
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.typing import SmarterDictType

MODULE = "smarter.apps.llmclient.management.commands.deploy_builtin_llmclients"
HERE = os.path.abspath(os.path.dirname(__file__))
SMARTER_PROJECT_WEBSEARCH_PATH = os.path.join(
    PROJECT_ROOT, "apps", "llmclient", "data", "plugins", "plugin-smarter-websearch.yaml"
)
SMARTER_LLMCLIENT_PATH = os.path.join(
    PROJECT_ROOT, "apps", "llmclient", "data", "llm-clients", "llmclient-smarter.yaml"
)
SIMPLE_LLMCLIENT_PATH = os.path.join(PROJECT_ROOT, "apps", "llmclient", "data", "llm-clients", "llmclient-simple.yaml")


class TestBuiltinLLMClientManifests(TestAccountMixin):
    """Test that every built-in llmclient manifest validates, so that none fails in production."""

    def test_every_manifest_validates(self):
        paths = sorted(glob.glob(os.path.join(PROJECT_ROOT, "apps", "llmclient", "data", "llm-clients", "*.yaml")))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(manifest=os.path.basename(path)):
                SAMLLMClient(**SAMLoader(file_path=path).pydantic_model_dump())


class TestDeployBuiltinLLMClients(TestAccountMixin):
    """Test that deploy_builtin_llmclients applies each built-in manifest on its own."""

    def setUp(self):
        super().setUp()
        self.command = Command(stdout=StringIO(), stderr=StringIO())
        self.command.user_profile = self.user_profile

    def write_manifest(self, manifest: SmarterDictType) -> str:
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
            path = SMARTER_LLMCLIENT_PATH
            self.assertFalse(self.command.create_and_deploy_llmclient(path))

    def test_llmclient_is_applied_as_deployed(self):
        """Test that a built-in llmclient manifest is applied with deployed set to true, rather than as it is."""
        self.assertFalse(get_readonly_yaml_file(SIMPLE_LLMCLIENT_PATH)["spec"]["config"]["prompt"]["deployed"])
        with (
            patch.object(Command, "apply_manifest", return_value=True) as apply_manifest,
            patch(f"{MODULE}.LLMClient.objects.get"),
        ):
            self.assertTrue(self.command.create_and_deploy_llmclient(SIMPLE_LLMCLIENT_PATH))
        manifest = apply_manifest.call_args.args[0]
        self.assertTrue(manifest.json_data["spec"]["config"]["prompt"]["deployed"])
        self.assertIn("deployed: true", manifest.yaml_data)
        # the built-in manifest itself is unchanged.
        self.assertFalse(get_readonly_yaml_file(SIMPLE_LLMCLIENT_PATH)["spec"]["config"]["prompt"]["deployed"])

    def test_deployed_llmclient_is_not_undeployed(self):
        """
        Test that deploying a built-in llmclient that is deployed queues neither an undeploy nor a deploy.

        Applying a built-in manifest, which is not deployed, and then deploying the llmclient
        queued an undeploy task, which destroyed the llmclient's A record, and then a deploy task,
        which created it again.
        """
        name = f"test_deploy_builtin_simple_{self.hash_suffix}"
        manifest = copy.deepcopy(get_readonly_yaml_file(SIMPLE_LLMCLIENT_PATH))
        manifest["metadata"]["name"] = name
        path = self.write_manifest(manifest)
        # apply_manifest applies built-in manifests as the smarter admin.
        user_profile = smarter_cached_objects.smarter_admin_user_profile
        self.command.user_profile = user_profile

        with (
            patch("smarter.apps.llmclient.receivers.deploy_default_api") as deploy_default_api,
            patch("smarter.apps.llmclient.receivers.undeploy_default_api") as undeploy_default_api,
            patch("smarter.apps.llmclient.receivers.delete_default_api"),
            patch(f"{MODULE}.deploy_default_api") as redeploy_default_api,
        ):
            # deleted while delete_default_api is patched, so that no task is queued.
            self.addCleanup(LLMClient.objects.filter(name=name).delete)
            self.assertTrue(self.command.create_and_deploy_llmclient(path), self.command.stderr.getvalue())  # type: ignore[union-attr]
            llmclient = LLMClient.objects.get(user_profile=user_profile, name=name)
            self.assertTrue(llmclient.deployed)
            deploy_default_api.delay.assert_called_once()
            redeploy_default_api.delay.assert_not_called()
            deploy_default_api.reset_mock()

            # deploying it again, e.g. when production is redeployed, once its domain is verified, changes nothing.
            LLMClient.objects.filter(id=llmclient.id).update(
                dns_verification_status=LLMClient.DnsVerificationStatusChoices.VERIFIED
            )
            self.assertTrue(self.command.create_and_deploy_llmclient(path), self.command.stderr.getvalue())  # type: ignore[union-attr]
            self.assertTrue(LLMClient.objects.get(user_profile=user_profile, name=name).deployed)
            deploy_default_api.delay.assert_not_called()
            undeploy_default_api.delay.assert_not_called()
            redeploy_default_api.delay.assert_not_called()
            LLMClient.objects.filter(name=name).delete()

    def test_deployed_llmclient_with_unverified_domain_is_redeployed(self):
        """
        Test that a deployed llmclient whose domain is not verified, or failed to verify, is deployed again.

        Its ``deployed`` doesn't change, so ``LLMClient.save()`` queues nothing, and its domain stayed
        unverified for good.
        """
        name = f"test_deploy_builtin_unverified_{self.hash_suffix}"
        manifest = copy.deepcopy(get_readonly_yaml_file(SIMPLE_LLMCLIENT_PATH))
        manifest["metadata"]["name"] = name
        path = self.write_manifest(manifest)
        user_profile = smarter_cached_objects.smarter_admin_user_profile
        self.command.user_profile = user_profile

        with (
            patch("smarter.apps.llmclient.receivers.deploy_default_api"),
            patch("smarter.apps.llmclient.receivers.undeploy_default_api"),
            patch("smarter.apps.llmclient.receivers.delete_default_api"),
            patch(f"{MODULE}.deploy_default_api") as redeploy_default_api,
        ):
            self.addCleanup(LLMClient.objects.filter(name=name).delete)
            self.assertTrue(self.command.create_and_deploy_llmclient(path), self.command.stderr.getvalue())  # type: ignore[union-attr]
            llmclient = LLMClient.objects.get(user_profile=user_profile, name=name)
            for status in Command.UNVERIFIED_DNS_STATUSES:
                with self.subTest(status=status):
                    redeploy_default_api.reset_mock()
                    LLMClient.objects.filter(id=llmclient.id).update(dns_verification_status=status)
                    self.assertTrue(self.command.create_and_deploy_llmclient(path))
                    redeploy_default_api.delay.assert_called_once_with(llmclient_id=llmclient.id)
            # a domain that is being verified is left to the task that is verifying it.
            redeploy_default_api.reset_mock()
            LLMClient.objects.filter(id=llmclient.id).update(
                dns_verification_status=LLMClient.DnsVerificationStatusChoices.VERIFYING
            )
            self.assertTrue(self.command.create_and_deploy_llmclient(path))
            redeploy_default_api.delay.assert_not_called()
            LLMClient.objects.filter(name=name).delete()

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
        path = SMARTER_LLMCLIENT_PATH
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

    def test_handle_fails_when_a_manifest_fails(self):
        """Test that every manifest is attempted, and that the command then fails, listing the failures."""
        with (
            patch(f"{MODULE}.glob.glob", side_effect=[["plugin.yaml"], ["bad.yaml", "good.yaml"]]),
            patch.object(Command, "create_plugin", return_value=True),
            patch.object(
                Command, "create_and_deploy_llmclient", side_effect=[False, True]
            ) as create_and_deploy_llmclient,
            self.assertRaises(CommandError) as ctx,
        ):
            call_command("deploy_builtin_llmclients", account_number=self.account.account_number, stdout=StringIO())
        self.assertEqual(create_and_deploy_llmclient.call_count, 2)
        self.assertIn("bad.yaml", str(ctx.exception))
        self.assertNotIn("good.yaml", str(ctx.exception))

    def test_handle_requires_account_number(self):
        with self.assertRaises(SmarterValueError):
            call_command("deploy_builtin_llmclients", account_number="", stdout=StringIO(), stderr=StringIO())
