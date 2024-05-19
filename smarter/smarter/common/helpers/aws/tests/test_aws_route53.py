# pylint: disable=wrong-import-position
# pylint: disable=duplicate-code
"""Test aws route 53 helpers."""

# python stuff
import os
import sys
import unittest
from pathlib import Path


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402

from smarter.common.helpers.aws_helpers import aws_helper  # noqa: E402


class TestAWSRoute53(unittest.TestCase):
    """Test AWS Route53 helper functions."""

    def setUp(self):
        """Setup the test."""
        self.root_domain = aws_helper.aws.root_domain
        self.root_hosted_zone = aws_helper.route53.get_hosted_zone(self.root_domain)
        self.root_hosted_zone_id = aws_helper.route53.get_hosted_zone_id(self.root_hosted_zone)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------
    def test_get_hosted_zone(self):
        """Test that we can access a Route53 hosted zone."""
        hosted_zone = aws_helper.route53.get_hosted_zone(self.root_domain)
        self.assertIsNotNone(hosted_zone)
        self.assertIn(hosted_zone["Name"], [self.root_domain, self.root_domain + "."])

    def test_get_or_create_hosted_zone(self):
        """Test that we can retrieve an existing Route53 hosted zone."""
        hosted_zone, created = aws_helper.route53.get_or_create_hosted_zone(self.root_domain)
        self.assertIsNotNone(hosted_zone)
        self.assertFalse(created)
        self.assertIn(hosted_zone["Name"], [self.root_domain, self.root_domain + "."])

    def test_get_dns_record(self):
        """Test that we can get an existing DNS record."""
        record = aws_helper.route53.get_dns_record(self.root_hosted_zone_id, self.root_domain, "NS")
        self.assertIsNotNone(record)
        self.assertIn(record["Name"], [self.root_domain, self.root_domain + "."])

    def test_get_ns_records(self):
        """Test that we can get the NS records for an existing hosted zone."""
        records = aws_helper.route53.get_ns_records(self.root_hosted_zone_id)
        self.assertIsNotNone(records)
        self.assertEqual(len(records), 4)

        records2 = aws_helper.route53.get_dns_record(self.root_hosted_zone_id, self.root_domain, "NS")
        self.assertIsNotNone(records2)
        self.assertEqual(records, records2["ResourceRecords"])

    def test_get_or_create_dns_record(self):
        """Test that we can get or create a DNS record."""
        ns_record = aws_helper.route53.get_dns_record(self.root_hosted_zone_id, self.root_domain, "NS")
        record, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=self.root_hosted_zone_id,
            record_name=self.root_domain,
            record_type="NS",
            record_ttl=ns_record["TTL"],
            record_value=ns_record["ResourceRecords"],
        )

        self.assertIsNotNone(record)
        self.assertTrue(created)
        self.assertIn(record["Name"], [self.root_domain, self.root_domain + "."])
        self.assertEqual(record["Type"], "NS")
        self.assertEqual(record["TTL"], ns_record["TTL"])
        self.assertEqual(record["ResourceRecords"], ns_record["ResourceRecords"])

    def test_get_hosted_zone_for_domain(self):
        """Test that we can get the hosted zone for a domain."""
        hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(self.root_domain)
        self.assertIsNotNone(hosted_zone_id)
        self.assertEqual(hosted_zone_id, self.root_hosted_zone_id)
