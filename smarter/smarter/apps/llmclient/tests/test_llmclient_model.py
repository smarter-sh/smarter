"""Test the LLMClient model's billing, domain, mode and readiness properties."""

from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.common.const import SmarterEnvironments


class TestLLMClientModel(TestAccountMixin):
    """Test LLMClient's properties, without saving changes that would deploy it."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_llmclient_model_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)

    def test_is_billable_resource(self):
        self.assertTrue(self.llmclient.is_billable_resource)

    def test_base_api_domain_in_aws(self):
        """In an AWS environment the base api domain is the environment's api domain."""
        settings = MagicMock(
            environment=list(SmarterEnvironments.aws_environments)[0], environment_api_domain="alpha.api.example.com"
        )
        with patch("smarter.apps.llmclient.models.llmclient.smarter_settings", settings):
            self.assertEqual(self.llmclient.base_api_domain, "alpha.api.example.com")

    def test_mode_of_an_unrelated_url(self):
        """A url that isn't the LLMClient's default, sandbox or custom url is of unknown mode."""
        self.assertEqual(self.llmclient.mode("https://unrelated.example.com/"), LLMClient.Modes.UNKNOWN)
        self.assertEqual(self.llmclient.mode(""), LLMClient.Modes.UNKNOWN)

    def test_ready_needs_deployment(self):
        """Outside the sandbox, a verified and certified LLMClient is ready only once deployed."""
        llmclient = self.llmclient
        llmclient.dns_verification_status = LLMClient.DnsVerificationStatusChoices.VERIFIED
        llmclient.tls_certificate_issuance_status = LLMClient.TlsCertificateIssuanceStatusChoices.ISSUED
        with patch.object(LLMClient, "mode", return_value=LLMClient.Modes.DEFAULT):
            llmclient.deployed = False
            self.assertFalse(llmclient.ready)
            llmclient.deployed = True
            self.assertTrue(llmclient.ready)
