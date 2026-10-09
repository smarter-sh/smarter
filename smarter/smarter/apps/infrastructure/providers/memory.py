"""
A cloud provider in memory, for tests and local development without a cloud account.

Its DNS zones, records and certificates are kept in memory, and behave like a cloud's, so that
tests exercise the service layer, and its signals, without reaching real infrastructure.

.. code-block:: python

    from smarter.apps.infrastructure.providers import configure_provider
    from smarter.apps.infrastructure.providers.memory import InMemoryProvider

    provider = InMemoryProvider()
    configure_provider(lambda: provider)
    provider.dns.add_zone("example.com")
    provider.certificates.issue_all = True
"""

import copy
from typing import Any, Optional

from ..const import CertificateStatus, CloudProviders
from ..services.base import DiscoveredResource
from ..services.certificates import Certificate, CertificateService
from ..services.dns import DNSRecord, DNSService, DNSZone, normalize_name
from .base import CloudProvider

ACCOUNT_ID = "000000000000"


class InMemoryDNSService(DNSService):
    """DNS zones and records in memory."""

    record_wait_seconds = 0

    def __init__(self, provider: "InMemoryProvider", **kwargs):
        super().__init__(provider_name=provider.provider_name, **kwargs)
        self.provider = provider
        self.zones: dict[str, DNSZone] = {}
        self.records: dict[str, list[DNSRecord]] = {}

    @property
    def ready(self) -> bool:
        return self.provider.ready

    def add_zone(self, domain: str, a_record: Optional[list[str]] = None) -> DNSZone:
        """Add a zone, e.g. the environment's API domain, optionally with an A record."""
        zone = self._create_zone(domain)
        if a_record:
            self._upsert_record(zone.id, DNSRecord(name=domain, type="A", ttl=600, values=a_record), create=True)
        return zone

    def _find_zone(self, domain: str) -> Optional[DNSZone]:
        domain = normalize_name(domain)
        return next((copy.deepcopy(z) for z in self.zones.values() if z.name == domain), None)

    def _find_zone_by_id(self, zone_id: str) -> Optional[DNSZone]:
        zone = self.zones.get(zone_id)
        return copy.deepcopy(zone) if zone else None

    def _create_zone(self, domain: str) -> DNSZone:
        zone_id = f"Z{len(self.zones) + 1:012d}"
        name_servers = [f"ns-{i}.memory-dns.example" for i in range(1, 5)]
        zone = DNSZone(id=zone_id, name=domain, name_servers=name_servers)
        self.zones[zone_id] = zone
        self.records[zone_id] = [DNSRecord(name=domain, type="NS", ttl=172800, values=name_servers)]
        return copy.deepcopy(zone)

    def _delete_zone(self, zone: DNSZone) -> None:
        self.zones.pop(zone.id, None)
        self.records.pop(zone.id, None)

    def _list_records(self, zone_id: str) -> list[DNSRecord]:
        return copy.deepcopy(self.records.get(zone_id, []))

    def _upsert_record(self, zone_id: str, record: DNSRecord, create: bool) -> None:
        records = self.records.setdefault(zone_id, [])
        records[:] = [r for r in records if (r.name, r.type) != (record.name, record.type)]
        records.append(copy.deepcopy(record))

    def _delete_record(self, zone_id: str, record: DNSRecord) -> None:
        records = self.records.get(zone_id, [])
        records[:] = [r for r in records if (r.name, r.type) != (record.name, record.type)]


class InMemoryCertificateService(CertificateService):
    """TLS certificates in memory, issued once their validation records exist, or at once with :attr:`issue_all`."""

    validation_wait_seconds = 0
    issue_wait_seconds = 0

    def __init__(self, provider: "InMemoryProvider", dns: DNSService, **kwargs):
        super().__init__(provider.provider_name, dns, **kwargs)
        self.provider = provider
        self.certificates: dict[str, Certificate] = {}
        self.issue_all = False
        """Issue every certificate, whether or not its validation records exist."""

    @property
    def ready(self) -> bool:
        return self.provider.ready

    def _find_certificate_id(self, domain_name: str) -> Optional[str]:
        domain_name = normalize_name(domain_name)
        return next((c.id for c in self.certificates.values() if c.domain_name == domain_name), None)

    def _request_certificate(self, domain_name: str) -> str:
        domain_name = normalize_name(domain_name)
        certificate_id = f"memory:certificate/{len(self.certificates) + 1}"
        self.certificates[certificate_id] = Certificate(
            id=certificate_id,
            domain_name=domain_name,
            status=CertificateStatus.PENDING_VALIDATION,
            validation_records=[
                DNSRecord(name=f"_validation.{domain_name}", type="CNAME", values=[f"_{len(self.certificates)}.memory"])
            ],
        )
        return certificate_id

    def _validated(self, certificate: Certificate) -> bool:
        zone = self.dns.get_zone(certificate.domain_name)
        if zone is None:
            return False
        return all(
            self.dns.get_record(zone.id, record.name, record.type) is not None
            for record in certificate.validation_records
        )

    def _describe_certificate(self, certificate_id: str) -> Optional[Certificate]:
        certificate = self.certificates.get(certificate_id)
        if certificate is None:
            return None
        if certificate.status == CertificateStatus.PENDING_VALIDATION and (
            self.issue_all or self._validated(certificate)
        ):
            certificate.status = CertificateStatus.ISSUED
        return copy.deepcopy(certificate)

    def _delete_certificate(self, certificate_id: str) -> None:
        self.certificates.pop(certificate_id, None)


class InMemoryProvider(CloudProvider):
    """
    A cloud provider in memory.

    :param ready: Whether the provider is authenticated.
    """

    name = CloudProviders.MEMORY

    def __init__(self, ready: bool = True, **kwargs):
        super().__init__(allow_in_tests=True, **kwargs)
        self._ready = ready
        self._dns = InMemoryDNSService(self)
        self._certificates = InMemoryCertificateService(self, self._dns)
        self.kubeconfig_updates = 0
        self.cluster_info: dict[str, Any] = {
            "health": {"issues": []},
            "platformVersion": "memory",
            "status": "ACTIVE",
            "version": "1.33",
        }
        self.cluster_resources: dict[str, list[DiscoveredResource]] = {}
        """The cloud resources of the cluster, by resource type, for the inventory."""

    @property
    def ready(self) -> bool:
        return self.authentication_state(self.identity, error="the in-memory provider is not ready")

    @ready.setter
    def ready(self, value: bool) -> None:
        self._ready = value

    @property
    def identity(self) -> Optional[dict[str, Any]]:
        return {"Account": ACCOUNT_ID, "Arn": f"memory::{ACCOUNT_ID}:user/smarter"} if self._ready else None

    @property
    def account_id(self) -> Optional[str]:
        return ACCOUNT_ID if self._ready else None

    @property
    def sdk_version(self) -> str:
        return "memory"

    @property
    def dns(self) -> InMemoryDNSService:
        return self._dns

    @property
    def certificates(self) -> InMemoryCertificateService:
        return self._certificates

    def update_kubeconfig(self) -> bool:
        self.kubeconfig_updates += 1
        return self._ready

    def get_kubernetes_cluster_info(self) -> dict[str, Any]:
        self.require_ready()
        return dict(self.cluster_info)

    def get_kubernetes_cluster_resources(self) -> dict[str, list[DiscoveredResource]]:
        if not self.ready:
            return {}
        return copy.deepcopy(self.cluster_resources)


__all__ = ["InMemoryCertificateService", "InMemoryDNSService", "InMemoryProvider"]
