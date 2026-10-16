"""
Test the verify_dns_configuration management command.

The cloud is never called: the command's infrastructure services use an
:class:`~smarter.apps.infrastructure.providers.memory.InMemoryProvider`, whose DNS zones and
records are in memory, so that the command's DNS operations really run.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.infrastructure.models import InfrastructureResource
from smarter.apps.infrastructure.providers.memory import InMemoryProvider
from smarter.apps.infrastructure.services.dns import DNSRecord
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterConfigurationError

from .base import CommandTestBase

MODULE = "smarter.apps.api.management.commands.verify_dns_configuration"
LOAD_BALANCER = ["192.0.2.10"]


def settings(environment: str) -> MagicMock:
    return MagicMock(
        environment=environment,
        root_domain="example.com",
        root_platform_domain="platform.example.com",
        root_api_domain="api.platform.example.com",
        root_proxy_domain="proxy.example.com",
        proxy_api_domain="api.proxy.example.com",
        environment_platform_domain="alpha.platform.example.com",
        environment_api_domain="alpha.api.platform.example.com",
        all_domains=["example.com", "api.platform.example.com"],
    )


class TestVerifyDnsConfiguration(CommandTestBase):
    """Test that the platform's DNS zones exist, and are delegated from their parents."""

    def setUp(self):
        super().setUp()
        self.provider = InMemoryProvider()
        self.dns = self.provider.dns
        self.dns.add_zone("example.com", a_record=LOAD_BALANCER)
        self.use(self.provider)
        self.addCleanup(InfrastructureResource.objects.filter(provider="memory").delete)

    def use(self, provider: InMemoryProvider, ready: bool = True) -> MagicMock:
        """Give the command a provider's services."""
        infrastructure = MagicMock(ready=ready, dns=provider.dns)
        patcher = patch(f"{MODULE}.infrastructure", infrastructure)
        patcher.start()
        self.addCleanup(patcher.stop)
        return infrastructure

    def run_in(self, environment: str) -> str:
        with patch(f"{MODULE}.smarter_settings", settings(environment)):
            return self.run_command("verify_dns_configuration")

    def assert_delegated(self, child: str, parent: str):
        """The child's zone has the load balancer's A record, and the parent has the child's NS records."""
        child_zone = self.dns.get_zone(child)
        parent_zone = self.dns.get_zone(parent)
        self.assertIsNotNone(child_zone, child)
        self.assertIsNotNone(parent_zone, parent)
        self.assertEqual(self.dns.get_record(child_zone.id, child, "A").values, LOAD_BALANCER)
        ns_record = self.dns.get_record(parent_zone.id, child, "NS")
        self.assertIsNotNone(ns_record, f"{parent} does not delegate {child}")
        self.assertEqual(sorted(ns_record.values), sorted(child_zone.name_servers))

    def test_aws_environment(self):
        """Test that every domain is verified, and delegated from its parent, in a cloud environment."""
        output = self.run_in(SmarterEnvironments.ALPHA)
        self.assertIn("alpha.api.platform.example.com", output)
        self.assert_delegated("platform.example.com", "example.com")
        self.assert_delegated("proxy.example.com", "example.com")
        self.assert_delegated("api.proxy.example.com", "proxy.example.com")
        self.assert_delegated("api.platform.example.com", "platform.example.com")
        self.assert_delegated("alpha.platform.example.com", "platform.example.com")
        self.assert_delegated("alpha.api.platform.example.com", "api.platform.example.com")
        root_zone = self.dns.get_zone("example.com")
        self.assertIsNone(
            self.dns.get_record(root_zone.id, "api.platform.example.com", "NS"),
            "the root zone must not delegate the api domain, which is below the delegated platform domain",
        )

    def test_idempotent(self):
        """Test that a second run verifies what the first created, rather than creating it again."""
        self.run_in(SmarterEnvironments.ALPHA)
        zones = dict(self.dns.zones)
        self.run_in(SmarterEnvironments.ALPHA)
        self.assertEqual(self.dns.zones, zones)

    def test_existing_a_records_are_not_overwritten(self):
        """
        Test that an existing A record in a child zone is left unchanged, even when it differs from the root domain's.

        The root domain, e.g. smarter.sh, may be served by a CDN rather than the platform's load
        balancer. Copying its A record over the child zones' records takes the platform offline.
        """
        cdn = ["198.51.100.1"]
        provider = InMemoryProvider()
        provider.dns.add_zone("example.com", a_record=cdn)
        provider.dns.add_zone("platform.example.com", a_record=LOAD_BALANCER)
        provider.dns.add_zone("api.platform.example.com", a_record=LOAD_BALANCER)
        self.use(provider)
        self.run_in(SmarterEnvironments.ALPHA)
        for domain in ("platform.example.com", "api.platform.example.com"):
            zone = provider.dns.get_zone(domain)
            self.assertEqual(provider.dns.get_record(zone.id, domain, "A").values, LOAD_BALANCER, domain)

    def test_new_zones_copy_the_platform_domain_a_record(self):
        """Test that new zones copy the platform domain's A record, not the root domain's, e.g. a CDN."""
        cdn = ["198.51.100.1"]
        provider = InMemoryProvider()
        provider.dns.add_zone("example.com", a_record=cdn)
        provider.dns.add_zone("platform.example.com", a_record=LOAD_BALANCER)
        self.use(provider)
        self.dns = provider.dns
        self.run_in(SmarterEnvironments.ALPHA)
        self.assert_delegated("api.platform.example.com", "platform.example.com")
        self.assert_delegated("proxy.example.com", "example.com")
        self.assert_delegated("alpha.api.platform.example.com", "api.platform.example.com")
        root_zone = provider.dns.get_zone("example.com")
        self.assertEqual(provider.dns.get_record(root_zone.id, "example.com", "A").values, cdn)

    def test_a_record_pointing_elsewhere_is_reported_not_verified(self):
        """
        Test that a child zone whose A record points elsewhere, e.g. at a CDN, is reported, rather than verified.

        Its delegation is still verified, and its A record is left unchanged.
        """
        cdn = ["198.51.100.1"]
        provider = InMemoryProvider()
        provider.dns.add_zone("example.com", a_record=LOAD_BALANCER)
        provider.dns.add_zone("platform.example.com", a_record=LOAD_BALANCER)
        provider.dns.add_zone("proxy.example.com", a_record=cdn)
        self.use(provider)
        output = self.run_in(SmarterEnvironments.ALPHA)

        self.assertIn("does not point at the platform's load balancer. Left it unchanged.", output)
        self.assertNotIn("verified A record for proxy.example.com", output)
        self.assertIn("verified A record for platform.example.com", output)
        summary = [line for line in output.splitlines() if "verified platform level DNS infrastructure" in line]
        self.assertEqual(len(summary), 1)
        verified = summary[0].split("following domains: ", 1)[1].strip().split(", ")
        self.assertNotIn("proxy.example.com", verified)
        self.assertIn("api.proxy.example.com", verified)
        self.assertIn(
            "A record left unchanged because it does not point at the platform's load balancer: proxy.example.com",
            output,
        )
        zone = provider.dns.get_zone("proxy.example.com")
        self.assertEqual(provider.dns.get_record(zone.id, "proxy.example.com", "A").values, cdn)
        root_zone = provider.dns.get_zone("example.com")
        self.assertIsNotNone(provider.dns.get_record(root_zone.id, "proxy.example.com", "NS"))

    def test_local_environment(self):
        """Test that only the proxy domains are verified in the local environment."""
        output = self.run_in(SmarterEnvironments.LOCAL)
        self.assertIn("proxy.example.com", output)
        self.assert_delegated("api.proxy.example.com", "proxy.example.com")
        self.assertIsNone(self.dns.get_zone("platform.example.com"))
        self.assertIsNone(self.dns.get_zone("api.platform.example.com"))

    def test_cloud_not_configured(self):
        """Test that the command does nothing when the cloud provider is not configured."""
        self.use(self.provider, ready=False)
        with patch(f"{MODULE}.smarter_settings", settings(SmarterEnvironments.LOCAL)):
            self.run_command("verify_dns_configuration")
        self.assertEqual(len(self.dns.zones), 1)

    def test_missing_root_zone(self):
        """Test that a root domain without a zone fails the command, rather than creating the zone."""
        empty = InMemoryProvider()
        self.use(empty)
        with self.assertRaises(SystemExit):
            self.run_in(SmarterEnvironments.ALPHA)
        self.assertEqual(empty.dns.zones, {})

    def test_missing_a_record(self):
        """Test that a root domain without an A record fails the command."""
        provider = InMemoryProvider()
        provider.dns.add_zone("example.com")
        self.use(provider)
        with self.assertRaises(SystemExit):
            self.run_in(SmarterEnvironments.ALPHA)

    def test_dns_not_ready(self):
        """Test that the command fails when the DNS service is not ready."""
        self.use(InMemoryProvider(ready=False), ready=True)
        with self.assertRaises(SystemExit):
            self.run_in(SmarterEnvironments.ALPHA)

    def test_get_any_A_record(self):  # pylint: disable=invalid-name
        from smarter.apps.api.management.commands.verify_dns_configuration import (  # pylint: disable=import-outside-toplevel
            Command,
        )

        command = Command()
        with patch(f"{MODULE}.smarter_settings", settings(SmarterEnvironments.ALPHA)):
            a_record = command.get_any_A_record()
            self.assertIsInstance(a_record, DNSRecord)
            self.assertEqual(a_record.values, LOAD_BALANCER)
            self.use(InMemoryProvider())
            with self.assertRaises(SmarterConfigurationError):
                command.get_any_A_record()
            self.use(InMemoryProvider(ready=False))
            with self.assertRaises(SmarterConfigurationError):
                command.get_any_A_record()
