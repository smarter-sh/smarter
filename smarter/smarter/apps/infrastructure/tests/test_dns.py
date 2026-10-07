"""Test :mod:`smarter.apps.infrastructure.services.dns`, with the in-memory provider's DNS."""

from unittest.mock import MagicMock, patch

from smarter.apps.infrastructure.const import CloudProviders
from smarter.apps.infrastructure.exceptions import (
    DNSRecordTimeout,
    DNSServiceError,
    DNSZoneNotFound,
    InfrastructureNotReadyError,
)
from smarter.apps.infrastructure.models import InfrastructureResource
from smarter.apps.infrastructure.services.dns import DNSRecord, DNSZone, normalize_name
from smarter.apps.infrastructure.signals import (
    billable_resource_created,
    billable_resource_creating,
    billable_resource_destroyed,
    billable_resource_destroying,
    infrastructure_operation_failed,
    resource_created,
    resource_destroyed,
)
from smarter.common.const import SmarterEnvironments
from smarter.lib.django.validators import SmarterValueError

from .base import InfrastructureTestBase

DNS_MODULE = "smarter.apps.infrastructure.services.dns"
LOAD_BALANCER = ["192.0.2.10"]


class TestDNSDataClasses(InfrastructureTestBase):
    """Test DNSZone, DNSRecord and normalize_name()."""

    def test_names_are_normalized(self):
        self.assertEqual(normalize_name("Example.COM."), "example.com")
        zone = DNSZone(id="Z1", name="Example.com.", name_servers=["NS-1.Example.net."])
        self.assertEqual((zone.name, zone.name_servers), ("example.com", ["ns-1.example.net"]))
        record = DNSRecord(name="www.example.com.", type="cname", values=["target.example.com."])
        self.assertEqual((record.name, record.type), ("www.example.com", "CNAME"))

    def test_same_target(self):
        a = DNSRecord(name="a", type="A", values=["1.1.1.1", "2.2.2.2"])
        self.assertTrue(a.same_target(DNSRecord(name="a", type="A", values=["2.2.2.2", "1.1.1.1"])))
        self.assertFalse(a.same_target(DNSRecord(name="a", type="A", values=["3.3.3.3"])))
        alias = DNSRecord(name="a", type="A", alias={"DNSName": "lb"})
        self.assertTrue(alias.same_target(DNSRecord(name="a", type="A", alias={"DNSName": "lb"})))
        self.assertFalse(alias.same_target(a))
        # trailing dots do not matter, e.g. NS values.
        ns = DNSRecord(name="a", type="NS", values=["ns-1.example.net."])
        self.assertTrue(ns.same_target(DNSRecord(name="a", type="NS", values=["ns-1.example.net"])))


class TestDNSZones(InfrastructureTestBase):
    """Test the zone operations, and their billable resource signals."""

    def setUp(self):
        super().setUp()
        self.dns = self.provider.dns

    def test_get_or_create_zone(self):
        """A new zone is billable: it is announced before and after it is created, and recorded in the ledger."""
        events = self.capture(billable_resource_creating, billable_resource_created)
        zone, created = self.dns.get_or_create_zone("example.com")
        self.assertTrue(created)
        self.assertEqual(zone.name, "example.com")
        self.assertEqual(len(zone.name_servers), 4)
        self.assertEqual([signal for signal, _ in events], [billable_resource_creating, billable_resource_created])
        created_event = self.sent(events, billable_resource_created)[0]
        self.assertEqual(created_event["resource_type"], "dns.zone")
        self.assertEqual(created_event["resource_id"], zone.id)
        self.assertEqual(created_event["provider"], CloudProviders.MEMORY)
        ledger = InfrastructureResource.objects.get(resource_type="dns.zone", resource_name="example.com")
        self.assertTrue(ledger.billable)
        self.assertEqual(ledger.status, InfrastructureResource.Status.ACTIVE)

        # the second time, the zone is found.
        events.clear()
        again, created = self.dns.get_or_create_zone("example.com.")
        self.assertFalse(created)
        self.assertEqual(again.id, zone.id)
        self.assertEqual(events, [])

    def test_get_zone(self):
        self.assertIsNone(self.dns.get_zone("example.com"))
        zone = self.dns.add_zone("example.com")
        self.assertEqual(self.dns.get_zone("example.com").id, zone.id)
        self.assertEqual(self.dns.get_zone_by_id(zone.id).name, "example.com")
        self.assertIsNone(self.dns.get_zone_by_id("ZNOPE"))

    def test_get_name_servers(self):
        zone = self.dns.add_zone("example.com")
        self.assertEqual(self.dns.get_name_servers(zone.id), zone.name_servers)
        with self.assertRaises(DNSZoneNotFound):
            self.dns.get_name_servers("ZNOPE")

    def test_delete_zone(self):
        """Deleting a zone is announced as the destruction of a billable resource, and recorded."""
        zone, _ = self.dns.get_or_create_zone("example.com")
        events = self.capture(billable_resource_destroying, billable_resource_destroyed)
        self.assertTrue(self.dns.delete_zone("example.com"))
        self.assertEqual([signal for signal, _ in events], [billable_resource_destroying, billable_resource_destroyed])
        self.assertIsNone(self.dns.get_zone("example.com"))
        ledger = InfrastructureResource.objects.get(resource_type="dns.zone", resource_name="example.com")
        self.assertEqual(ledger.status, InfrastructureResource.Status.DESTROYED)
        self.assertIsNotNone(ledger.destroyed_at)
        self.assertEqual(ledger.resource_id, zone.id)
        # a zone that does not exist is not deleted.
        self.assertFalse(self.dns.delete_zone("example.com"))

    def test_not_ready(self):
        self.provider.ready = False
        self.assertFalse(self.dns.ready)
        with self.assertRaises(InfrastructureNotReadyError):
            self.dns.get_zone("example.com")
        with self.assertRaises(InfrastructureNotReadyError):
            self.dns.get_zone_by_id("Z1")
        with self.assertRaises(InfrastructureNotReadyError):
            self.dns.list_records("Z1")

    def test_provider_errors_are_translated(self):
        """A provider's own exception is raised as a DNSServiceError, and announced."""
        events = self.capture(infrastructure_operation_failed)
        with patch.object(self.dns, "_find_zone", side_effect=RuntimeError("throttled")):
            with self.assertRaises(DNSServiceError) as context:
                self.dns.get_zone("example.com")
        self.assertIn("throttled", str(context.exception))
        failure = self.sent(events, infrastructure_operation_failed)[0]
        self.assertEqual(failure["operation"], "get_zone")


class TestDNSRecords(InfrastructureTestBase):
    """Test the record operations."""

    def setUp(self):
        super().setUp()
        self.dns = self.provider.dns
        self.zone = self.dns.add_zone("example.com", a_record=LOAD_BALANCER)

    def test_get_or_create_record(self):
        """A record is created, then found while it matches, and updated when it does not."""
        events = self.capture(resource_created)
        record, created = self.dns.get_or_create_record(self.zone.id, "www.example.com.", "a", values=["192.0.2.1"])
        self.assertTrue(created)
        self.assertEqual((record.name, record.type, record.values), ("www.example.com", "A", ["192.0.2.1"]))
        self.assertEqual(len(self.sent(events, resource_created)), 1)
        self.assertEqual(self.sent(events, resource_created)[0]["resource_name"], "www.example.com A")

        found, created = self.dns.get_or_create_record(self.zone.id, "www.example.com", "A", values=["192.0.2.1"])
        self.assertFalse(created)
        self.assertEqual(found, record)
        self.assertEqual(len(self.sent(events, resource_created)), 1)

        updated, created = self.dns.get_or_create_record(self.zone.id, "www.example.com", "A", values=["192.0.2.2"])
        self.assertFalse(created)
        self.assertEqual(updated.values, ["192.0.2.2"])
        self.assertEqual(len(self.sent(events, resource_created)), 2)
        # the ledger has one active row, updated, rather than two.
        self.assertEqual(
            InfrastructureResource.objects.filter(resource_name="www.example.com A", status="active").count(), 1
        )

    def test_alias_record(self):
        alias = {"DNSName": "lb.example.net", "HostedZoneId": "ZLB"}
        record, created = self.dns.get_or_create_record(self.zone.id, "api.example.com", "A", ttl=300, alias=alias)
        self.assertTrue(created)
        self.assertEqual(record.alias, alias)
        self.assertIsNone(record.ttl)

    def test_record_names_may_have_underscores(self):
        """Validation records, e.g. ACME's, have labels that host names may not."""
        record, _ = self.dns.get_or_create_record(self.zone.id, "_acme-challenge.example.com", "TXT", values=["token"])
        self.assertEqual(record.name, "_acme-challenge.example.com")

    def test_record_timeout(self):
        """A record that never appears in its zone times out, after the configured attempts."""
        self.dns.record_wait_attempts = 3
        sleep = MagicMock()
        with (
            patch.object(self.dns, "_upsert_record"),
            patch.object(self.dns, "_sleep", sleep),
        ):
            with self.assertRaises(DNSRecordTimeout):
                self.dns.get_or_create_record(self.zone.id, "www.example.com", "A", values=["192.0.2.1"])
        self.assertEqual(sleep.call_count, 2)

    def test_record_appears_after_waiting(self):
        """A record that takes a moment to appear is waited for."""
        self.dns.record_wait_attempts = 3
        original = self.dns._list_records  # pylint: disable=protected-access
        calls = {"n": 0}

        def slow_list(zone_id):
            calls["n"] += 1
            # the first lookup is before the upsert, the second right after it.
            return [] if calls["n"] <= 2 else original(zone_id)

        with patch.object(self.dns, "_list_records", side_effect=slow_list), patch.object(self.dns, "_sleep") as sleep:
            record, created = self.dns.get_or_create_record(self.zone.id, "www.example.com", "A", values=["192.0.2.1"])
        self.assertTrue(created)
        self.assertEqual(record.values, ["192.0.2.1"])
        sleep.assert_called_once()

    def test_delete_record(self):
        self.dns.get_or_create_record(self.zone.id, "www.example.com", "A", values=["192.0.2.1"])
        events = self.capture(resource_destroyed)
        self.assertTrue(self.dns.delete_record(self.zone.id, "www.example.com", "A"))
        self.assertIsNone(self.dns.get_record(self.zone.id, "www.example.com", "A"))
        self.assertEqual(len(self.sent(events, resource_destroyed)), 1)
        self.assertFalse(self.dns.delete_record(self.zone.id, "www.example.com", "A"))

    def test_get_environment_a_record(self):
        self.assertEqual(self.dns.get_environment_a_record("example.com").values, LOAD_BALANCER)
        self.assertIsNone(self.dns.get_environment_a_record("other.example.org"))

    def test_create_domain_a_record(self):
        """A host's A record is a copy of its parent domain's, in the parent's zone."""
        record, created = self.dns.create_domain_a_record("app.example.com", "example.com")
        self.assertTrue(created)
        self.assertEqual(record.values, LOAD_BALANCER)
        self.assertEqual(self.dns.get_record(self.zone.id, "app.example.com", "A").values, LOAD_BALANCER)
        _, created = self.dns.create_domain_a_record("app.example.com", "example.com")
        self.assertFalse(created)

    def test_create_domain_a_record_in_another_zone(self):
        """E.g.

        a custom domain's host gets the platform's A record, in the custom domain's own zone.
        """
        custom = self.dns.add_zone("customer.example.org")
        self.dns.create_domain_a_record("app.customer.example.org", "example.com", zone_id=custom.id)
        self.assertEqual(self.dns.get_record(custom.id, "app.customer.example.org", "A").values, LOAD_BALANCER)
        self.assertIsNone(self.dns.get_record(self.zone.id, "app.customer.example.org", "A"))

    def test_create_domain_a_record_without_parent_a_record(self):
        self.dns.add_zone("bare.example.org")
        with self.assertRaises(DNSZoneNotFound):
            self.dns.create_domain_a_record("app.bare.example.org", "bare.example.org")


class TestResolveDomain(InfrastructureTestBase):
    """Test that domains are validated, and that local domains are resolved to their proxy domains."""

    def settings(self, environment) -> MagicMock:
        return MagicMock(
            environment=environment,
            environment_api_domain="api.localhost:9357",
            root_domain="example.com",
            local_hosts=["localhost", "127.0.0.1", "localhost:9357"],
        )

    def test_local_environment_proxy_domain(self):
        with patch(f"{DNS_MODULE}.smarter_settings", self.settings(SmarterEnvironments.LOCAL)):
            dns = self.provider.dns
            self.assertEqual(dns.environment_api_domain, "local.api.example.com")
            self.assertEqual(dns.resolve_domain("app.api.localhost:9357"), "app.local.api.example.com")
            self.assertEqual(dns.resolve_record_name("_x.app.api.localhost:9357."), "_x.app.local.api.example.com")

    def test_ordinary_domain(self):
        with patch(f"{DNS_MODULE}.smarter_settings", self.settings(SmarterEnvironments.ALPHA)):
            self.assertEqual(self.provider.dns.resolve_domain("app.example.com"), "app.example.com")

    def test_local_hosts_are_prohibited(self):
        with patch(f"{DNS_MODULE}.smarter_settings", self.settings(SmarterEnvironments.ALPHA)):
            for domain in ("localhost", "127.0.0.1"):
                with self.subTest(domain=domain):
                    with self.assertRaises(SmarterValueError):
                        self.provider.dns.resolve_domain(domain)
                    with self.assertRaises(SmarterValueError):
                        self.provider.dns.resolve_record_name(domain)

    def test_invalid_domain(self):
        with patch(f"{DNS_MODULE}.smarter_settings", self.settings(SmarterEnvironments.ALPHA)):
            with self.assertRaises(SmarterValueError):
                self.provider.dns.resolve_domain("not a domain!")
