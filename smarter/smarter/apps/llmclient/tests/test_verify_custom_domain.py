"""
Test :mod:`smarter.apps.llmclient.tasks.verify_custom_domain`.

The task is called directly, which runs it synchronously, in this process. AWS, DNS and email are mocked.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient, LLMClientCustomDomain
from smarter.apps.llmclient.tasks.verify_custom_domain import verify_custom_domain

MODULE = "smarter.apps.llmclient.tasks.verify_custom_domain"


class TestVerifyCustomDomain(TestAccountMixin):
    """Test that a custom domain is checked once per run, and that its account is notified of the result."""

    def setUp(self):
        super().setUp()
        self.hosted_zone_id = f"ZTEST{self.hash_suffix}".upper()
        self.domain = LLMClientCustomDomain.objects.create(
            aws_hosted_zone_id=self.hosted_zone_id, domain_name=f"test-{self.hash_suffix}.example.com"
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=self.domain.pk).delete)
        self.llmclient = LLMClient.objects.create(
            name=f"test_verify_custom_domain_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        LLMClient.objects.filter(pk=self.llmclient.pk).update(custom_domain=self.domain)

        aws_helper = MagicMock()
        aws_helper.route53.get_hosted_zone_by_id.return_value = {"HostedZone": {"Name": self.domain.domain_name}}
        for target, value in (
            ("is_taskable", MagicMock(return_value=True)),
            ("aws_helper", aws_helper),
            ("AccountContact", MagicMock()),
        ):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)
        patcher = patch.object(verify_custom_domain, "apply_async")
        self.apply_async = patcher.start()
        self.addCleanup(patcher.stop)

    def test_not_verified_checks_again(self):
        """Test that a domain whose name servers have not changed yet is checked again later, rather than waited for."""
        with patch(f"{MODULE}._ns_records_verified", return_value=False):
            self.assertIsNone(verify_custom_domain(self.hosted_zone_id, sleep_interval=60, max_attempts=3))
        self.apply_async.assert_called_once()
        kwargs = self.apply_async.call_args.kwargs
        self.assertEqual((kwargs["kwargs"]["attempt"], kwargs["countdown"]), (1, 60))
        self.AccountContact.send_email_to_account.assert_not_called()

    def test_verified_notifies_the_account(self):
        """Test that a verified domain is marked as verified, and that the account of its llmclient is notified."""
        with patch(f"{MODULE}._ns_records_verified", return_value=True):
            self.assertTrue(verify_custom_domain(self.hosted_zone_id))
        self.assertTrue(LLMClientCustomDomain.objects.get(pk=self.domain.pk).is_verified)
        self.AccountContact.send_email_to_account.assert_called_once()
        self.assertEqual(self.AccountContact.send_email_to_account.call_args.kwargs["account"], self.account)

    def test_failure_after_last_attempt_notifies_the_account(self):
        """Test that a domain that is still not verified after the last check fails, and that its account is notified."""
        with patch(f"{MODULE}._ns_records_verified", return_value=False):
            self.assertFalse(verify_custom_domain(self.hosted_zone_id, max_attempts=3, attempt=2))
        self.apply_async.assert_not_called()
        self.AccountContact.send_email_to_account.assert_called_once()
        self.assertIn("Failure", self.AccountContact.send_email_to_account.call_args.kwargs["subject"])
