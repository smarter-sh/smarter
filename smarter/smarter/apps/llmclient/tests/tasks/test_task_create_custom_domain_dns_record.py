"""
Test :mod:`smarter.apps.llmclient.tasks.create_custom_domain_dns_record`.

The task is called directly, which runs it synchronously. AWS Route53 is mocked.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClientCustomDomain
from smarter.apps.llmclient.tasks.create_custom_domain_dns_record import (
    create_custom_domain_dns_record,
)
from smarter.apps.llmclient.tasks.exceptions import LLMClientCustomDomainNotFound
from smarter.common.helpers.aws.route53 import AWSRoute53

MODULE = "smarter.apps.llmclient.tasks.create_custom_domain_dns_record"


class TestCreateCustomDomainDnsRecord(TestAccountMixin):
    """Test that the DNS record of a custom domain is gotten or created in its hosted zone."""

    def setUp(self):
        super().setUp()
        self.custom_domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile,
            aws_hosted_zone_id="Z0000000000TEST",
            domain_name=f"test-dns-{self.hash_suffix}.example.com",
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=self.custom_domain.pk).delete)
        self.aws_helper = MagicMock()
        self.aws_helper.route53 = MagicMock(spec=AWSRoute53)
        self.aws_helper.route53.get_or_create_dns_record.return_value = (
            {"Name": "www.example.com.", "Type": "A", "ResourceRecords": [{"Value": "192.0.2.1"}], "TTL": 600},
            True,
        )
        for target, value in (("is_taskable", MagicMock(return_value=True)), ("aws_helper", self.aws_helper)):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def create(self, custom_domain_id: int):
        return create_custom_domain_dns_record(custom_domain_id, "www.example.com.", "A", "192.0.2.1", 600)

    def test_not_taskable(self):
        self.is_taskable.return_value = False
        self.assertIsNone(self.create(self.custom_domain.pk))
        self.aws_helper.route53.get_or_create_dns_record.assert_not_called()

    def test_route53_not_available(self):
        self.aws_helper.route53 = None
        self.assertIsNone(self.create(self.custom_domain.pk))

    def test_unknown_custom_domain(self):
        with self.assertRaises(LLMClientCustomDomainNotFound):
            self.create(999999999)
        self.aws_helper.route53.get_or_create_dns_record.assert_not_called()

    def test_record_created_in_hosted_zone(self):
        """Test that the record is gotten or created in the custom domain's hosted zone."""
        self.create(self.custom_domain.pk)
        self.aws_helper.route53.get_or_create_dns_record.assert_called_once_with(
            hosted_zone_id="Z0000000000TEST",
            record_name="www.example.com.",
            record_type="A",
            record_value="192.0.2.1",
            record_ttl=600,
        )
