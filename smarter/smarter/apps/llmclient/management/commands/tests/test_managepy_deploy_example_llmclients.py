"""
Test :mod:`smarter.apps.llmclient.management.commands.deploy_example_llmclients`.

The command deploys the example LLMClients that exist, and creates nothing. The deploy tasks,
which would create DNS records, are patched.
"""

import glob
import os
import shutil
import tempfile
from io import StringIO
from unittest.mock import patch

import yaml
from django.core.management import call_command
from django.core.management.base import CommandError

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.const import EXAMPLE_LLMCLIENTS_PATH
from smarter.apps.llmclient.management.commands.deploy_example_llmclients import Command
from smarter.apps.llmclient.manifest.models.llmclient.model import SAMLLMClient
from smarter.apps.llmclient.models import LLMClient
from smarter.common.exceptions import SmarterValueError
from smarter.lib.manifest.loader import SAMLoader

MODULE = "smarter.apps.llmclient.management.commands.deploy_example_llmclients"
RECEIVERS = "smarter.apps.llmclient.receivers"


class TestExampleLLMClientManifests(TestAccountMixin):
    """Test that every example llmclient manifest validates, so that none fails in production."""

    def test_every_manifest_validates(self):
        paths = sorted(glob.glob(os.path.join(EXAMPLE_LLMCLIENTS_PATH, "*.yaml")))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(manifest=os.path.basename(path)):
                SAMLLMClient(**SAMLoader(file_path=path).pydantic_model_dump())


class TestDeployExampleLLMClients(TestAccountMixin):
    """Test that deploy_example_llmclients deploys the example LLMClients that exist."""

    def setUp(self):
        super().setUp()
        self.name = f"test_deploy_example_{self.hash_suffix}".lower()
        self.path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.path)
        self.stackademy_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.stackademy_path)
        self.write_manifest(self.name)
        for name, path in (("EXAMPLE_LLMCLIENTS_PATH", self.path), ("STACKADEMY_PATH", self.stackademy_path)):
            patcher = patch(f"{MODULE}.{name}", path)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target in ("deploy_default_api", "undeploy_default_api", "delete_default_api"):
            patcher = patch(f"{RECEIVERS}.{target}")
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)
        patcher = patch(f"{MODULE}.deploy_default_api")
        self.redeploy_default_api = patcher.start()
        self.addCleanup(patcher.stop)
        # deleted while delete_default_api is patched, so that no task is queued.
        self.addCleanup(lambda: LLMClient.objects.filter(name__startswith="test_deploy_example_").delete())

    def write_manifest(self, name: str, extensions: tuple[str, ...] = (), path: str = "") -> None:
        """Write an example LLMClient manifest, named ``name``, into ``path``, by default the patched examples folder."""
        manifest = {
            "apiVersion": "smarter.sh/v1",
            "kind": "LLMClient",
            "metadata": {"name": name, "description": "a test LLMClient", "version": "1.0.0"},
            "spec": {"config": {"prompt": {"deployed": False}}, "extensions": list(extensions)},
        }
        with open(os.path.join(path or self.path, f"{name}.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(manifest, f)

    def run_command(self) -> str:
        out = StringIO()
        call_command("deploy_example_llmclients", account_number=self.account.account_number, stdout=out, stderr=out)
        return out.getvalue()

    def llmclient(self, **fields) -> LLMClient:
        return LLMClient.objects.create(name=self.name, user_profile=self.user_profile, **fields)

    def test_deploys_an_llmclient_that_is_not_deployed(self):
        llmclient = self.llmclient()
        output = self.run_command()
        llmclient.refresh_from_db()
        self.assertTrue(llmclient.deployed)
        self.deploy_default_api.delay.assert_called_once()
        self.assertIn(f"Deploying LLMClient {self.name}", output)

    def test_deploys_the_stackademy_llmclients(self):
        """Test that the Stackademy LLMClients, in their own folder, are deployed too."""
        self.llmclient()
        stackademy = LLMClient.objects.create(name=f"{self.name}_stackademy", user_profile=self.user_profile)
        self.write_manifest(f"{self.name}_stackademy", path=self.stackademy_path)
        output = self.run_command()
        stackademy.refresh_from_db()
        self.assertTrue(stackademy.deployed)
        self.assertIn(f"Deploying LLMClient {self.name}_stackademy", output)

    def test_deployed_llmclient_is_left_as_it_is(self):
        """Test that a deployed LLMClient whose domain is verified queues neither an undeploy nor a deploy."""
        self.llmclient(deployed=True, dns_verification_status=LLMClient.DnsVerificationStatusChoices.VERIFIED)
        self.deploy_default_api.reset_mock()
        output = self.run_command()
        self.deploy_default_api.delay.assert_not_called()
        self.undeploy_default_api.delay.assert_not_called()
        self.redeploy_default_api.delay.assert_not_called()
        self.assertIn(f"LLMClient {self.name} is deployed", output)

    def test_deployed_llmclient_with_unverified_domain_is_redeployed(self):
        """Test that a deployed llmclient whose domain is not verified, or failed to verify, is deployed again."""
        llmclient = self.llmclient(deployed=True)
        for status in (*Command.UNVERIFIED_DNS_STATUSES, LLMClient.DnsVerificationStatusChoices.VERIFYING):
            with self.subTest(status=status):
                self.redeploy_default_api.reset_mock()
                LLMClient.objects.filter(id=llmclient.id).update(dns_verification_status=status)
                self.run_command()
                if status == LLMClient.DnsVerificationStatusChoices.VERIFYING:
                    # a domain that is being verified is left to the task that is verifying it.
                    self.redeploy_default_api.delay.assert_not_called()
                else:
                    self.redeploy_default_api.delay.assert_called_once_with(llmclient_id=llmclient.id)

    def test_missing_llmclient_fails(self):
        """Test that every LLMClient is attempted, and that one that does not exist fails the command."""
        self.write_manifest(f"{self.name}_missing")
        llmclient = self.llmclient()
        with self.assertRaises(CommandError) as ctx:
            self.run_command()
        self.assertIn(f"{self.name}_missing.yaml", str(ctx.exception))
        llmclient.refresh_from_db()
        self.assertTrue(llmclient.deployed)

    def test_missing_llmclient_that_needs_an_extension_is_skipped(self):
        """Test that an LLMClient that add_example_llmclients skipped, for its missing extension, is skipped."""
        self.write_manifest(f"{self.name}_extension", extensions=(f"no-such-extension-{self.hash_suffix}",))
        self.llmclient()
        output = self.run_command()
        self.assertIn("needs extensions that are not installed", output)

    def test_deploy_failure_fails(self):
        """Test that an LLMClient that fails to deploy fails the command."""
        self.llmclient()
        with patch.object(LLMClient, "save", side_effect=RuntimeError("boom")), self.assertRaises(CommandError):
            self.run_command()

    def test_unknown_account(self):
        with self.assertRaises(SmarterValueError):
            call_command("deploy_example_llmclients", account_number="9999-9999-9999", stdout=StringIO())

    def test_creates_nothing(self):
        """Test that an example LLMClient that does not exist is not created."""
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertFalse(LLMClient.objects.filter(name=self.name).exists())
