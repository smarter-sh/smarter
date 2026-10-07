"""
Test :mod:`smarter.apps.llmclient.tasks.create_custom_domain_dns_record`.

The task is called directly, which runs it synchronously. The DNS service is mocked.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.infrastructure.services.dns import DNSRecord
from smarter.apps.llmclient.models import (
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
)
from smarter.apps.llmclient.tasks.create_custom_domain_dns_record import (
    create_custom_domain_dns_record,
)
from smarter.apps.llmclient.tasks.exceptions import LLMClientCustomDomainNotFound

MODULE = "smarter.apps.llmclient.tasks.create_custom_domain_dns_record"


class TestCreateCustomDomainDnsRecord(TestAccountMixin):
    """Test that the DNS record of a custom domain is gotten or created in its DNS zone."""

    def setUp(self):
        super().setUp()
        self.custom_domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile,
            aws_hosted_zone_id="Z0000000000TEST",
            domain_name=f"test-dns-{self.hash_suffix}.example.com",
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=self.custom_domain.pk).delete)
        self.infrastructure = MagicMock()
        self.infrastructure.dns.get_or_create_record.return_value = (
            DNSRecord(name="www.example.com", type="A", ttl=600, values=["192.0.2.1"]),
            True,
        )
        for target, value in (("is_taskable", MagicMock(return_value=True)), ("infrastructure", self.infrastructure)):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def create(self, custom_domain_id: int, value: str = "192.0.2.1"):
        return create_custom_domain_dns_record(custom_domain_id, "www.example.com.", "A", value, 600)

    def test_not_taskable(self):
        self.is_taskable.return_value = False
        self.assertIsNone(self.create(self.custom_domain.pk))
        self.infrastructure.dns.get_or_create_record.assert_not_called()

    def test_unknown_custom_domain(self):
        with self.assertRaises(LLMClientCustomDomainNotFound):
            self.create(999999999)
        self.infrastructure.dns.get_or_create_record.assert_not_called()

    def test_record_created_in_zone(self):
        """Test that the record is gotten or created in the custom domain's zone, and saved."""
        self.create(self.custom_domain.pk)
        self.infrastructure.dns.get_or_create_record.assert_called_once_with(
            zone_id="Z0000000000TEST",
            name="www.example.com.",
            record_type="A",
            ttl=600,
            values=["192.0.2.1"],
        )
        dns_record = LLMClientCustomDomainDNS.objects.get(custom_domain=self.custom_domain)
        self.assertEqual(dns_record.record_name, "www.example.com")
        self.assertEqual(dns_record.record_value, "192.0.2.1")

    def test_record_updated(self):
        """Test that an existing record's value is updated, rather than recorded twice."""
        self.create(self.custom_domain.pk)
        self.infrastructure.dns.get_or_create_record.return_value = (
            DNSRecord(name="www.example.com", type="A", ttl=300, values=["192.0.2.2"]),
            False,
        )
        self.create(self.custom_domain.pk, value="192.0.2.2")
        dns_record = LLMClientCustomDomainDNS.objects.get(custom_domain=self.custom_domain)
        self.assertEqual(dns_record.record_value, "192.0.2.2")
        self.assertEqual(dns_record.record_ttl, 300)
