"""
Test the add_builtin_custom_domains management command.

The manifests are really applied, with apply_manifest, but verify_custom_domain is not queued.
"""

import glob
import os
from io import StringIO
from unittest.mock import patch

import yaml
from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.const import CUSTOM_DOMAINS_PATH
from smarter.apps.llmclient.models import LLMClientCustomDomain

MODULE = "smarter.apps.llmclient.management.commands.add_builtin_custom_domains"
Status = LLMClientCustomDomain.VerificationStatusChoices


class TestAddBuiltinCustomDomains(TestAccountMixin):
    """Test that the built-in CustomDomains are applied, and that their verification starts."""

    def setUp(self):
        super().setUp()
        self.addCleanup(LLMClientCustomDomain.objects.filter(user_profile=self.user_profile).delete)
        patcher = patch(f"{MODULE}.verify_custom_domain")
        self.verify_custom_domain = patcher.start()
        self.addCleanup(patcher.stop)

    def run_command(self, **options) -> str:
        out = StringIO()
        call_command("add_builtin_custom_domains", stdout=out, stderr=out, **options)
        return out.getvalue()

    def test_example_com_manifest(self):
        """The example.com manifest is a valid CustomDomain manifest."""
        filespec = os.path.join(CUSTOM_DOMAINS_PATH, "example-com.yaml")
        with open(filespec, encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
        self.assertEqual(manifest["kind"], "CustomDomain")
        self.assertEqual(manifest["metadata"]["name"], "example_com")
        self.assertEqual(manifest["spec"]["config"]["domainName"], "example.com")

    def test_applies_and_starts_verification(self):
        output = self.run_command(username=self.admin_user.username)
        manifests = glob.glob(os.path.join(CUSTOM_DOMAINS_PATH, "*.yaml"))
        self.assertTrue(manifests)
        self.assertNotIn("failed to apply", output)
        custom_domain = LLMClientCustomDomain.objects.get(user_profile=self.user_profile, name="example_com")
        self.assertEqual(custom_domain.domain_name, "example.com")
        self.assertEqual(custom_domain.aws_hosted_zone_id, "")
        self.assertEqual(custom_domain.verification_status, Status.VERIFYING)
        self.verify_custom_domain.delay.assert_called_once_with(custom_domain_id=custom_domain.pk)

    def test_reapplying_does_not_duplicate(self):
        self.run_command(username=self.admin_user.username)
        self.run_command(username=self.admin_user.username)
        self.assertEqual(
            LLMClientCustomDomain.objects.filter(user_profile=self.user_profile, name="example_com").count(), 1
        )

    def test_verified_domain_is_not_verified_again(self):
        self.run_command(username=self.admin_user.username)
        custom_domain = LLMClientCustomDomain.objects.get(user_profile=self.user_profile, name="example_com")
        custom_domain.set_verification_status(Status.VERIFIED)
        self.verify_custom_domain.reset_mock()
        self.run_command(username=self.admin_user.username)
        self.verify_custom_domain.delay.assert_not_called()

    def test_failed_manifests_are_reported(self):
        with patch(f"{MODULE}.call_command", side_effect=RuntimeError("invalid manifest")):
            output = self.run_command(username=self.admin_user.username)
        self.assertIn("failed to apply", output)
        self.assertIn("invalid manifest", output)
        self.verify_custom_domain.delay.assert_not_called()
