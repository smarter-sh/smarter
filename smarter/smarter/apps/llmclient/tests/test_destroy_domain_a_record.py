"""
Test :mod:`smarter.apps.llmclient.tasks.destroy_domain_a_record`.

The task is called directly, which runs it synchronously. AWS Route53 is mocked.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.llmclient.tasks.destroy_domain_a_record import (
    destroy_domain_A_record,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.llmclient.tasks.destroy_domain_a_record"
HOSTNAME = "test-llmclient.api.example.com"
API_HOST_DOMAIN = "api.example.com"


class TestDestroyDomainARecord(SmarterTestBase):
    """Test that the A record of a hostname is destroyed."""

    def setUp(self):
        super().setUp()
        self.aws_helper = MagicMock()
        self.aws_helper.aws.domain_resolver.side_effect = lambda domain_name: domain_name
        self.aws_helper.route53.get_hosted_zone_id_for_domain.return_value = "Z0000000000TEST"
        for target, value in (("is_taskable", MagicMock(return_value=True)), ("aws_helper", self.aws_helper)):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def test_not_taskable(self):
        self.is_taskable.return_value = False
        destroy_domain_A_record(HOSTNAME, API_HOST_DOMAIN)
        self.aws_helper.route53.get_hosted_zone_id_for_domain.assert_not_called()

    def test_route53_not_available(self):
        self.aws_helper.route53 = None
        self.assertIsNone(destroy_domain_A_record(HOSTNAME, API_HOST_DOMAIN))

    def test_record_not_found(self):
        """Test that a hostname without an A record has nothing destroyed."""
        self.aws_helper.route53.get_dns_record.return_value = None
        destroy_domain_A_record(HOSTNAME, API_HOST_DOMAIN)
        self.aws_helper.route53.destroy_dns_record.assert_not_called()

    def test_record_destroyed(self):
        """Test that the A record is destroyed with its type, ttl, alias target and resource records."""
        self.aws_helper.route53.get_dns_record.return_value = {
            "Type": "A",
            "TTL": 300,
            "AliasTarget": {"DNSName": "lb.example.com"},
            "ResourceRecords": None,
        }
        destroy_domain_A_record(HOSTNAME, API_HOST_DOMAIN, task_id="test-task")
        self.aws_helper.route53.destroy_dns_record.assert_called_once_with(
            hosted_zone_id="Z0000000000TEST",
            record_name=HOSTNAME,
            record_type="A",
            record_ttl=300,
            alias_target={"DNSName": "lb.example.com"},
            record_resource_records=None,
        )
