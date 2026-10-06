"""
Test :mod:`smarter.apps.llmclient.tasks.verify_domain`.

The task is called directly, which runs it synchronously, in this process. The DNS service and DNS resolution are mocked.
"""

from unittest.mock import MagicMock, patch

import dns.resolver

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.infrastructure.services.dns import DNSRecord, DNSZone
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.tasks.verify_domain import (
    VERIFY_DOMAIN_INTERVAL,
    VERIFY_DOMAIN_MAX_ATTEMPTS,
    DomainCheck,
    check_domain,
    verify_domain,
)

MODULE = "smarter.apps.llmclient.tasks.verify_domain"
DOMAIN = "example.3141-5926-5359.api.example.com"


class TestVerifyDomain(TestAccountMixin):
    """Test that a domain is checked once per run, and checked again later, rather than waited for."""

    def setUp(self):
        super().setUp()
        self.infrastructure = MagicMock()
        self.infrastructure.dns.resolve_domain.side_effect = lambda domain: domain
        for target, value in (("is_taskable", MagicMock(return_value=True)), ("infrastructure", self.infrastructure)):
            patcher = patch(f"{MODULE}.{target}", value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(verify_domain, "apply_async")
        self.apply_async = patcher.start()
        self.addCleanup(patcher.stop)

    def test_check_domain(self):
        """Test the three results of one check: a missing record, a domain that does not resolve yet, and one that does."""
        dns_service = self.infrastructure.dns
        dns_service.get_record.return_value = None
        self.assertEqual(check_domain(DOMAIN, hosted_zone_id="Z1"), DomainCheck.MISSING)

        dns_service.get_record.return_value = DNSRecord(name=DOMAIN, type="A", values=["1.2.3.4"])
        for error in (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
            with self.subTest(error=error.__name__), patch(f"{MODULE}.dns.resolver.query", side_effect=error):
                self.assertEqual(check_domain(DOMAIN, hosted_zone_id="Z1"), DomainCheck.PENDING)

        record = MagicMock()
        record.to_text.return_value = "1.2.3.4"
        with patch(f"{MODULE}.dns.resolver.query", return_value=[record]):
            self.assertEqual(check_domain(DOMAIN, hosted_zone_id="Z1"), DomainCheck.VERIFIED)

    def test_check_domain_in_the_api_domain_zone(self):
        """Test that, without a zone, the record is looked up in the zone of the environment's API domain."""
        dns_service = self.infrastructure.dns
        dns_service.get_zone.return_value = None
        self.assertEqual(check_domain(DOMAIN), DomainCheck.MISSING)
        dns_service.get_record.assert_not_called()

        dns_service.get_zone.return_value = DNSZone(id="ZAPI", name="api.example.com")
        dns_service.get_record.return_value = None
        self.assertEqual(check_domain(DOMAIN), DomainCheck.MISSING)
        dns_service.get_record.assert_called_once_with("ZAPI", DOMAIN, "A")

    def test_pending_checks_again(self):
        """Test that a domain that does not resolve yet is checked again later, rather than waited for."""
        with patch(f"{MODULE}.check_domain", return_value=DomainCheck.PENDING):
            self.assertIsNone(verify_domain(DOMAIN, attempt=2))
        self.apply_async.assert_called_once()
        kwargs = self.apply_async.call_args.kwargs
        self.assertEqual(kwargs["kwargs"]["attempt"], 3)
        self.assertEqual(kwargs["countdown"], VERIFY_DOMAIN_INTERVAL)

    def test_pending_after_last_attempt_fails(self):
        """Test that a domain that still does not resolve after the last check fails, and its llmclient too."""
        llmclient = LLMClient.objects.create(
            name=f"test_verify_domain_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=llmclient.pk).delete)
        with patch(f"{MODULE}.check_domain", return_value=DomainCheck.PENDING):
            self.assertFalse(verify_domain(DOMAIN, llmclient_id=llmclient.pk, attempt=VERIFY_DOMAIN_MAX_ATTEMPTS - 1))
        self.apply_async.assert_not_called()
        self.assertEqual(
            LLMClient.objects.get(pk=llmclient.pk).dns_verification_status,
            LLMClient.DnsVerificationStatusChoices.FAILED,
        )

    def test_verified_activates(self):
        """Test that a domain that resolves activates its llmclient, when asked to."""
        llmclient = LLMClient.objects.create(
            name=f"test_verify_domain_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=llmclient.pk).delete)
        with patch(f"{MODULE}.check_domain", return_value=DomainCheck.VERIFIED):
            self.assertTrue(verify_domain(DOMAIN, llmclient_id=llmclient.pk, activate_llmclient=True))
        self.assertTrue(LLMClient.objects.get(pk=llmclient.pk).deployed)
        self.apply_async.assert_not_called()
