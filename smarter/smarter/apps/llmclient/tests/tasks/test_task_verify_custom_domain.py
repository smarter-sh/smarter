"""
Test :mod:`smarter.apps.llmclient.tasks.verify_custom_domain`.

The task is called directly, which runs it synchronously, in this process. AWS, DNS and email
are mocked.
"""

from unittest.mock import MagicMock, patch

import dns.resolver

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient, LLMClientCustomDomain
from smarter.apps.llmclient.tasks.exceptions import LLMClientTaskError
from smarter.apps.llmclient.tasks.verify_custom_domain import (
    _certificate_status,
    _ns_records_verified,
    _verification_blocker,
    verify_custom_domain,
)

MODULE = "smarter.apps.llmclient.tasks.verify_custom_domain"
Status = LLMClientCustomDomain.VerificationStatusChoices


class TestVerifyCustomDomain(TestAccountMixin):
    """Test that a custom domain is checked once per run, and that its owner is notified of the result."""

    def setUp(self):
        super().setUp()
        self.hosted_zone_id = f"ZTEST{self.hash_suffix}".upper()
        self.domain_name = f"test-{self.hash_suffix}.example.com".lower()
        self.domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile,
            aws_hosted_zone_id=self.hosted_zone_id,
            domain_name=self.domain_name,
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=self.domain.pk).delete)

        aws_helper = MagicMock()
        # Route53 reports hosted zone names with a trailing dot.
        aws_helper.route53.get_hosted_zone_by_id.return_value = {"HostedZone": {"Name": f"{self.domain_name}."}}
        aws_helper.route53.get_ns_records.return_value = [{"Value": "ns-1.awsdns.com."}]
        aws_helper.acm.get_certificate_arn.return_value = "arn:certificate"
        aws_helper.acm.certificate_status.return_value = "ISSUED"
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

    def refreshed(self) -> LLMClientCustomDomain:
        return LLMClientCustomDomain.objects.get(pk=self.domain.pk)

    # -------------------------------------------------------------------------
    # the task
    # -------------------------------------------------------------------------
    def test_not_verified_checks_again(self):
        """A domain that is not verified yet is Verifying, records why, and is checked again later."""
        with patch(f"{MODULE}._verification_blocker", return_value="The NS records are not delegated yet."):
            self.assertIsNone(verify_custom_domain(self.hosted_zone_id, sleep_interval=60, max_attempts=3))
        self.apply_async.assert_called_once()
        kwargs = self.apply_async.call_args.kwargs
        self.assertEqual((kwargs["kwargs"]["attempt"], kwargs["countdown"]), (1, 60))
        domain = self.refreshed()
        self.assertEqual(domain.verification_status, Status.VERIFYING)
        self.assertEqual(domain.verification_message, "The NS records are not delegated yet.")
        self.assertIsNone(domain.verified_at)
        self.AccountContact.send_email_to_account.assert_not_called()

    def test_verified_notifies_the_owner(self):
        """A domain whose certificate is issued is Verified, with its time, and its owner is notified."""
        with patch(f"{MODULE}._verification_blocker", return_value=None):
            self.assertTrue(verify_custom_domain(self.hosted_zone_id))
        domain = self.refreshed()
        self.assertEqual(domain.verification_status, Status.VERIFIED)
        self.assertTrue(domain.is_verified)
        self.assertIsNotNone(domain.verified_at)
        self.assertEqual(domain.verification_message, "")
        self.assertIn(self.domain_name, LLMClientCustomDomain.get_verified_domains())
        # the domain's owner is notified, although no llmclient uses the domain.
        self.assertFalse(LLMClient.objects.filter(custom_domain=self.domain).exists())
        self.AccountContact.send_email_to_account.assert_called_once()
        self.assertEqual(self.AccountContact.send_email_to_account.call_args.kwargs["account"], self.account)

    def test_failure_after_last_attempt_notifies_the_owner(self):
        """A domain that is still not verified after the last check is Failed, and its owner is notified why."""
        with patch(f"{MODULE}._verification_blocker", return_value="The TLS certificate is not issued yet."):
            self.assertFalse(verify_custom_domain(self.hosted_zone_id, max_attempts=3, attempt=2))
        self.apply_async.assert_not_called()
        domain = self.refreshed()
        self.assertEqual(domain.verification_status, Status.FAILED)
        self.assertEqual(domain.verification_message, "The TLS certificate is not issued yet.")
        kwargs = self.AccountContact.send_email_to_account.call_args.kwargs
        self.assertIn("Failure", kwargs["subject"])
        self.assertIn("The TLS certificate is not issued yet.", kwargs["body"])

    def test_verified_domain_stays_verified_while_it_is_checked_again(self):
        """Re-verifying a Verified domain does not take it out of service until verification fails."""
        self.domain.set_verification_status(Status.VERIFIED)
        verified_at = self.refreshed().verified_at
        with patch(f"{MODULE}._verification_blocker", return_value="The TLS certificate is not issued yet."):
            self.assertIsNone(verify_custom_domain(self.hosted_zone_id, max_attempts=3))
        domain = self.refreshed()
        self.assertEqual(domain.verification_status, Status.VERIFIED)
        self.assertEqual(domain.verified_at, verified_at)

    def test_unregistered_domain_fails_at_once(self):
        """A custom domain without a hosted zone fails at once, without calling AWS, or checking again."""
        unregistered = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile, name="unregistered", domain_name=f"unregistered-{self.domain_name}"
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=unregistered.pk).delete)
        self.assertFalse(verify_custom_domain(custom_domain_id=unregistered.pk))
        unregistered.refresh_from_db()
        self.assertEqual(unregistered.verification_status, Status.FAILED)
        self.assertIn("no AWS Route53 hosted zone", unregistered.verification_message)
        self.aws_helper.route53.get_hosted_zone_by_id.assert_not_called()
        self.apply_async.assert_not_called()

    def test_registered_domain_by_id(self):
        """A custom domain with a hosted zone is verified by its id, as by its hosted zone."""
        with patch(f"{MODULE}._verification_blocker", return_value=None):
            self.assertTrue(verify_custom_domain(custom_domain_id=self.domain.pk))
        self.aws_helper.route53.get_hosted_zone_by_id.assert_called_once_with(hosted_zone_id=self.hosted_zone_id)
        self.assertEqual(self.refreshed().verification_status, Status.VERIFIED)

    def test_unknown_domain_id(self):
        self.assertFalse(verify_custom_domain(custom_domain_id=999999999))

    # -------------------------------------------------------------------------
    # the verification steps
    # -------------------------------------------------------------------------
    def test_ns_records_not_delegated(self):
        with patch(f"{MODULE}._ns_records_verified", return_value=False):
            blocker = _verification_blocker(self.hosted_zone_id, self.domain_name, None)
        self.assertIn("not delegated", blocker)
        self.assertIn("ns-1.awsdns.com.", blocker)

    def test_certificate_not_issued(self):
        self.aws_helper.acm.certificate_status.return_value = "PENDING_VALIDATION"
        with patch(f"{MODULE}._ns_records_verified", return_value=True):
            blocker = _verification_blocker(self.hosted_zone_id, self.domain_name, None)
        self.assertIn("PENDING_VALIDATION", blocker)

    def test_missing_certificate_is_requested(self):
        """A domain without a certificate gets one, with its DNS validation record."""
        self.aws_helper.acm.get_certificate_arn.return_value = None
        self.aws_helper.acm.get_or_create_certificate.return_value = "arn:new"
        self.aws_helper.acm.certificate_status.return_value = "PENDING_VALIDATION"
        with patch(f"{MODULE}._ns_records_verified", return_value=True):
            _verification_blocker(self.hosted_zone_id, self.domain_name, None)
        self.aws_helper.acm.get_or_create_certificate.assert_called_once_with(domain_name=self.domain_name)
        self.aws_helper.acm.get_or_create_certificate_dns_record.assert_called_once_with(certificate_arn="arn:new")

    def test_certificate_issued(self):
        """A domain whose NS records are delegated, and whose certificate is issued, is verified."""
        with patch(f"{MODULE}._ns_records_verified", return_value=True):
            self.assertIsNone(_verification_blocker(self.hosted_zone_id, self.domain_name, None))
        self.aws_helper.acm.certificate_status.assert_called_once_with(certificate_arn="arn:certificate")
        self.aws_helper.acm.get_or_create_certificate.assert_not_called()

    # -------------------------------------------------------------------------
    # preconditions and the individual checks
    # -------------------------------------------------------------------------
    def test_not_taskable(self):
        self.is_taskable.return_value = False
        self.assertFalse(verify_custom_domain(self.hosted_zone_id))

    def test_route53_unavailable(self):
        self.aws_helper.route53 = None
        self.assertFalse(verify_custom_domain(self.hosted_zone_id))

    def test_malformed_hosted_zone_raises(self):
        self.aws_helper.route53.get_hosted_zone_by_id.return_value = None
        with self.assertRaises(LLMClientTaskError):
            verify_custom_domain(self.hosted_zone_id)

    def test_hosted_zone_that_is_not_a_custom_domain(self):
        """A verified hosted zone with no custom domain is verified without notifying anyone."""
        with patch(f"{MODULE}._verification_blocker", return_value=None):
            self.assertTrue(verify_custom_domain(f"ZOTHER{self.hash_suffix}".upper()))
        self.AccountContact.send_email_to_account.assert_not_called()

    def ns_records_verified_with(self, **query_kwargs) -> bool:
        with patch(f"{MODULE}.dns.resolver.query", **query_kwargs):
            return _ns_records_verified(self.hosted_zone_id, self.domain_name, None)

    def test_ns_records_delegated(self):
        rdata = MagicMock()
        rdata.to_text.return_value = "ns-1.awsdns.com."
        self.assertTrue(self.ns_records_verified_with(return_value=[rdata]))

    def test_ns_records_delegated_elsewhere(self):
        rdata = MagicMock()
        rdata.to_text.return_value = "ns.elsewhere.com."
        self.assertFalse(self.ns_records_verified_with(return_value=[rdata]))

    def test_ns_records_query_failures(self):
        for error in (dns.resolver.NXDOMAIN(), dns.resolver.Timeout(), RuntimeError("boom")):
            with self.subTest(error=type(error).__name__):
                self.assertFalse(self.ns_records_verified_with(side_effect=error))

    def test_certificate_status_without_acm(self):
        self.aws_helper.acm = None
        self.assertIn("unavailable", _certificate_status(self.domain_name))
