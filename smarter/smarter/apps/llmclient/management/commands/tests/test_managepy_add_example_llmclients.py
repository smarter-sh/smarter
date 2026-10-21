"""
Test :mod:`smarter.apps.llmclient.management.commands.add_example_llmclients`.

The manifests are really applied, from a copy of an example LLMClient manifest with a test name.
The deploy and undeploy tasks, which would change DNS records, are patched.
"""

import copy
import glob
import os
import shutil
import tempfile
from io import StringIO
from unittest.mock import patch

import yaml
from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.const import EXAMPLE_LLMCLIENTS_PATH
from smarter.apps.llmclient.management.commands.add_example_llmclients import Command
from smarter.apps.llmclient.models import LLMClient
from smarter.common.utils import get_readonly_yaml_file

MODULE = "smarter.apps.llmclient.management.commands.add_example_llmclients"
RECEIVERS = "smarter.apps.llmclient.receivers"
SIMPLE_LLMCLIENT_PATH = os.path.join(EXAMPLE_LLMCLIENTS_PATH, "llmclient-simple.yaml")


class TestAddExampleLLMClients(TestAccountMixin):
    """Test that add_example_llmclients applies the example LLMClients, and deploys none."""

    def setUp(self):
        super().setUp()
        self.name = f"test_add_example_{self.hash_suffix}".lower()
        self.path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.path)
        patcher = patch(f"{MODULE}.EXAMPLE_LLMCLIENTS_PATH", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)
        for target in ("deploy_default_api", "undeploy_default_api", "delete_default_api"):
            patcher = patch(f"{RECEIVERS}.{target}")
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)
        # deleted while delete_default_api is patched, so that no task is queued.
        self.addCleanup(lambda: LLMClient.objects.filter(name__startswith="test_add_example_").delete())

    def write_manifest(self, name: str, **spec) -> None:
        """Write a copy of the simple example LLMClient, named ``name``, into the patched examples folder."""
        manifest = copy.deepcopy(get_readonly_yaml_file(SIMPLE_LLMCLIENT_PATH))
        manifest["metadata"]["name"] = name
        manifest["spec"].update(spec)
        with open(os.path.join(self.path, f"{name}.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(manifest, f)

    def run_command(self) -> str:
        out = StringIO()
        call_command("add_example_llmclients", username=self.admin_user.username, stdout=out, stderr=out)
        return out.getvalue()

    def test_applies_an_llmclient_without_deploying_it(self):
        self.write_manifest(self.name)
        self.run_command()
        llmclient = LLMClient.objects.get(user_profile=self.user_profile, name=self.name)
        self.assertFalse(llmclient.deployed)
        self.deploy_default_api.delay.assert_not_called()

    def test_deployed_llmclient_stays_deployed(self):
        """
        Test that applying the example of a deployed LLMClient doesn't undeploy it.

        The manifest is not deployed, so applying it as it is would queue an undeploy task, which
        destroys the LLMClient's A record.
        """
        self.write_manifest(self.name)
        self.run_command()
        LLMClient.objects.filter(user_profile=self.user_profile, name=self.name).update(deployed=True)
        self.run_command()
        self.assertTrue(LLMClient.objects.get(user_profile=self.user_profile, name=self.name).deployed)
        self.undeploy_default_api.delay.assert_not_called()

    def test_llmclient_that_needs_a_missing_extension_is_skipped(self):
        self.write_manifest(self.name, extensions=[f"no-such-extension-{self.hash_suffix}"])
        output = self.run_command()
        self.assertIn("needs extensions that are not installed", output)
        self.assertFalse(LLMClient.objects.filter(name=self.name).exists())

    def test_failure_is_reported_and_the_others_are_applied(self):
        """Test that a manifest that fails is reported, and doesn't prevent the others from being applied."""
        self.write_manifest(f"{self.name}_bad", plugins=[f"no_such_plugin_{self.hash_suffix}"])
        self.write_manifest(f"{self.name}_good")
        output = self.run_command()
        self.assertIn(f"{self.name}_bad.yaml", output)
        self.assertIn("failed to apply", output)
        self.assertFalse(LLMClient.objects.filter(name=f"{self.name}_bad").exists())
        self.assertTrue(LLMClient.objects.filter(name=f"{self.name}_good").exists())

    def test_applies_the_examples(self):
        """Test that the example LLMClients are applied, in the order of their files."""
        with (
            patch(f"{MODULE}.EXAMPLE_LLMCLIENTS_PATH", EXAMPLE_LLMCLIENTS_PATH),
            patch(f"{MODULE}.Command.missing_extensions", return_value=[]),
            patch(f"{MODULE}.Command.apply", return_value=None) as apply,
        ):
            self.run_command()
        filespecs = [call.args[0] for call in apply.call_args_list]
        examples = sorted(glob.glob(os.path.join(EXAMPLE_LLMCLIENTS_PATH, "*.yaml")))
        self.assertEqual(filespecs, examples)
        self.assertFalse([f for f in filespecs if "stackademy" in f])

    def test_keep_deployed_copies_the_manifest(self):
        """Test that keep_deployed sets deployed on a copy, and leaves the manifest as it was."""
        manifest = {"metadata": {"name": self.name}}
        kept = Command.keep_deployed(manifest, self.user_profile)
        self.assertEqual(kept["spec"]["config"]["prompt"]["deployed"], False)
        self.assertEqual(manifest, {"metadata": {"name": self.name}})
