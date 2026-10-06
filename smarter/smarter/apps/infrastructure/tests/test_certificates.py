"""Test :mod:`smarter.apps.infrastructure.services.certificates`, with the in-memory provider's certificates."""

from unittest.mock import patch

from smarter.apps.infrastructure.const import CertificateStatus
from smarter.apps.infrastructure.exceptions import (
    CertificateNotFound,
    CertificateServiceError,
    CertificateTimeout,
)
from smarter.apps.infrastructure.services.certificates import Certificate
from smarter.apps.infrastructure.services.dns import DNSRecord
from smarter.apps.infrastructure.signals import (
    billable_resource_creating,
    resource_created,
    resource_destroyed,
)

from .base import InfrastructureTestBase


class TestCertificateService(InfrastructureTestBase):
    """Test that certificates are requested, validated with DNS, issued and deleted."""

    def setUp(self):
        super().setUp()
        self.certificates = self.provider.certificates
        self.dns = self.provider.dns

    def test_get_or_create_certificate(self):
        """A certificate is requested once.

        Certificates are free, so there is no billable signal.
        """
        events = self.capture(billable_resource_creating, resource_created)
        self.assertIsNone(self.certificates.get_certificate_id("example.com"))
        certificate_id, created = self.certificates.get_or_create_certificate("Example.com.")
        self.assertTrue(created)
        self.assertEqual(self.sent(events, billable_resource_creating), [])
        created_event = self.sent(events, resource_created)[0]
        self.assertEqual(
            (created_event["resource_type"], created_event["resource_name"], created_event["resource_id"]),
            ("certificate", "example.com", certificate_id),
        )
        again, created = self.certificates.get_or_create_certificate("example.com")
        self.assertEqual(again, certificate_id)
        self.assertFalse(created)

    def test_validation_and_issue(self):
        """A certificate is issued once its validation records are in its domain's zone."""
        certificate_id, _ = self.certificates.get_or_create_certificate("example.com")
        self.assertEqual(self.certificates.certificate_status(certificate_id), CertificateStatus.PENDING_VALIDATION)
        self.assertFalse(self.certificates.is_issued(certificate_id))

        records = self.certificates.create_validation_records(certificate_id)
        self.assertEqual(len(records), 1)
        zone = self.dns.get_zone("example.com")
        self.assertIsNotNone(zone, "the zone is created for the validation records")
        self.assertIsNotNone(self.dns.get_record(zone.id, records[0].name, "CNAME"))
        self.assertTrue(self.certificates.is_issued(certificate_id))
        self.assertTrue(self.certificates.get_certificate(certificate_id).is_issued)

    def test_shared_validation_records_are_created_once(self):
        """A domain and its wildcard share one validation record."""
        record = DNSRecord(name="_x.example.com", type="CNAME", values=["_y.validations.example"])
        certificate = Certificate(
            id="cert", domain_name="example.com", status="PENDING_VALIDATION", validation_records=[record, record]
        )
        with patch.object(self.certificates, "_describe_certificate", return_value=certificate):
            records = self.certificates.create_validation_records("cert")
        self.assertEqual(len(records), 1)

    def test_wait_for_validation_records(self):
        """The provider generates validation records a few seconds after the request."""
        self.certificates.validation_wait_attempts = 3
        pending = Certificate(id="cert", domain_name="example.com", status="PENDING_VALIDATION")
        ready = Certificate(
            id="cert",
            domain_name="example.com",
            status="PENDING_VALIDATION",
            validation_records=[DNSRecord(name="_x.example.com", type="CNAME", values=["_y"])],
        )
        with (
            patch.object(self.certificates, "_describe_certificate", side_effect=[None, pending, ready]),
            patch.object(self.certificates, "_sleep") as sleep,
        ):
            self.assertEqual(self.certificates.wait_for_validation_records("cert"), ready)
        self.assertEqual(sleep.call_count, 2)

    def test_wait_for_validation_records_timeouts(self):
        self.certificates.validation_wait_attempts = 2
        pending = Certificate(id="cert", domain_name="example.com", status="PENDING_VALIDATION")
        with patch.object(self.certificates, "_describe_certificate", return_value=pending):
            with self.assertRaises(CertificateTimeout):
                self.certificates.wait_for_validation_records("cert")
        with patch.object(self.certificates, "_describe_certificate", return_value=None):
            with self.assertRaises(CertificateNotFound):
                self.certificates.wait_for_validation_records("cert")

    def test_wait_until_issued(self):
        certificate_id, _ = self.certificates.get_or_create_certificate("example.com")
        self.certificates.issue_wait_attempts = 3
        with patch.object(self.certificates, "_sleep") as sleep:
            self.assertFalse(self.certificates.wait_until_issued(certificate_id))
        self.assertEqual(sleep.call_count, 2)
        self.certificates.issue_all = True
        self.assertTrue(self.certificates.wait_until_issued(certificate_id))

    def test_unknown_certificate(self):
        with self.assertRaises(CertificateNotFound):
            self.certificates.get_certificate("nope")
        self.assertFalse(self.certificates.delete_certificate("nope"))

    def test_delete_certificate(self):
        certificate_id, _ = self.certificates.get_or_create_certificate("example.com")
        events = self.capture(resource_destroyed)
        self.assertTrue(self.certificates.delete_certificate(certificate_id))
        self.assertIsNone(self.certificates.get_certificate_id("example.com"))
        self.assertEqual(self.sent(events, resource_destroyed)[0]["resource_id"], certificate_id)

    def test_provider_errors_are_translated(self):
        with patch.object(self.certificates, "_request_certificate", side_effect=RuntimeError("limit exceeded")):
            with self.assertRaises(CertificateServiceError):
                self.certificates.get_or_create_certificate("example.com")
