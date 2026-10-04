"""
Test :mod:`smarter.apps.llmclient.tasks.undeploy_default_api`.

The task is called directly, which runs it synchronously, in this process. AWS is
mocked: no Route53 record is read or destroyed.
"""

from unittest.mock import patch
from urllib.parse import urlparse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.tasks import undeploy_default_api
from smarter.common.conf import smarter_settings

MODULE = "smarter.apps.llmclient.tasks.undeploy_default_api"


class TestUndeployDefaultApi(TestAccountMixin):
    """Test that undeploying an LLMClient destroys its default domain A record, and resets its state."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_undeploy_default_api_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        # update(), rather than save(), which would queue a real deployment of an llmclient that is deployed.
        LLMClient.objects.filter(pk=self.llmclient.pk).update(
            deployed=True, dns_verification_status=LLMClient.DnsVerificationStatusChoices.VERIFIED
        )
        patcher = patch(f"{MODULE}.is_taskable", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_undeploy(self):
        """Test that the default domain's A record is destroyed, and the llmclient is no longer deployed."""
        with patch(f"{MODULE}.destroy_domain_A_record") as destroy_domain_A_record:
            undeploy_default_api(llmclient_id=self.llmclient.pk)

        destroy_domain_A_record.assert_called_once()
        kwargs = destroy_domain_A_record.call_args.kwargs
        self.assertEqual(kwargs["hostname"], urlparse(self.llmclient.default_url).netloc)
        self.assertEqual(kwargs["api_host_domain"], smarter_settings.environment_api_domain)

        llmclient = LLMClient.objects.get(pk=self.llmclient.pk)
        self.assertFalse(llmclient.deployed)
        self.assertEqual(llmclient.dns_verification_status, LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED)

    def test_unknown_llmclient(self):
        """Test that undeploying an llmclient that does not exist destroys nothing."""
        with patch(f"{MODULE}.destroy_domain_A_record") as destroy_domain_A_record:
            self.assertIsNone(undeploy_default_api(llmclient_id=999999999))
        destroy_domain_A_record.assert_not_called()

    def test_not_taskable(self):
        """Test that nothing is done when AWS is not available."""
        with (
            patch(f"{MODULE}.is_taskable", return_value=False),
            patch(f"{MODULE}.destroy_domain_A_record") as destroy_domain_A_record,
        ):
            undeploy_default_api(llmclient_id=self.llmclient.pk)
        destroy_domain_A_record.assert_not_called()
        self.assertTrue(LLMClient.objects.get(pk=self.llmclient.pk).deployed)
