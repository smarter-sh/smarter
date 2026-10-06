"""
The DNS service: zones and records, in any cloud provider's DNS.

The platform uses :class:`DNSService`, through
:data:`smarter.apps.infrastructure.services.infrastructure` ``.dns``, and the provider's DNS
is an implementation of it, e.g.
:class:`~smarter.apps.infrastructure.providers.aws.dns.Route53DNSService`.

A provider implements only the primitives, the abstract ``_`` methods. The operations that the
platform needs, e.g. :meth:`DNSService.create_domain_a_record`, are built on them here, once,
along with their signals, so that they behave the same in every cloud.

Zones and records are :class:`DNSZone` and :class:`DNSRecord`, whatever the provider's own
representation. Names never have a trailing dot.
"""

import time
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_API_SUBDOMAIN, SmarterEnvironments
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator, SmarterValueError
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..const import DEFAULT_DNS_RECORD_TTL, InfrastructureServiceNames
from ..exceptions import DNSRecordTimeout, DNSServiceError, DNSZoneNotFound
from .base import InfrastructureService

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])

RESOURCE_TYPE_ZONE = "dns.zone"
RESOURCE_TYPE_RECORD = "dns.record"


def normalize_name(name: str) -> str:
    """A DNS name without its trailing dot, in lower case, e.g. ``Example.com.`` -> ``example.com``."""
    return str(name).rstrip(".").lower()


@dataclass
class DNSZone:
    """A DNS zone, e.g. an AWS Route53 hosted zone."""

    id: str
    """The provider's id of the zone, e.g. ``Z148QEXAMPLE8V``."""

    name: str
    """The zone's domain, e.g. ``example.com``."""

    name_servers: list[str] = field(default_factory=list)
    """The zone's authoritative name servers, which a parent domain delegates the zone to."""

    def __post_init__(self):
        self.name = normalize_name(self.name)
        self.name_servers = [normalize_name(ns) for ns in self.name_servers]


@dataclass
class DNSRecord:
    """A DNS record set: the values of one name and type."""

    name: str
    """The record's name, e.g. ``api.example.com``."""

    type: str
    """The record's type, e.g. ``A``, ``CNAME``, ``NS`` or ``TXT``."""

    ttl: Optional[int] = None
    """Seconds.

    None for an alias record.
    """

    values: list[str] = field(default_factory=list)
    """The record's values, e.g. IP addresses."""

    alias: Optional[dict[str, Any]] = None
    """A provider-specific alias target, e.g. an AWS load balancer, in place of values."""

    def __post_init__(self):
        self.name = normalize_name(self.name)
        self.type = str(self.type).upper()
        self.values = [str(value) for value in self.values]

    def same_target(self, other: "DNSRecord") -> bool:
        """Whether two records point at the same values, or the same alias."""
        if self.alias or other.alias:
            return self.alias == other.alias
        return {v.rstrip(".") for v in self.values} == {v.rstrip(".") for v in other.values}


class DNSService(InfrastructureService):
    """
    The DNS service of a cloud provider.

    :param provider_name: The name of the provider, e.g. ``aws``.
    """

    service_name = InfrastructureServiceNames.DNS
    error_class = DNSServiceError

    billable_zones: bool = True
    """Whether the provider bills for zones, e.g. AWS Route53 bills each hosted zone monthly."""

    record_wait_attempts: int = 10
    """How many times to look for a new record, before :class:`DNSRecordTimeout`."""

    record_wait_seconds: float = 15
    """Seconds between the attempts."""

    # --------------------------------------------------------------------------
    # primitives, which a provider implements
    # --------------------------------------------------------------------------
    @abstractmethod
    def _find_zone(self, domain: str) -> Optional[DNSZone]:
        """Return the zone of a domain, or None."""

    @abstractmethod
    def _find_zone_by_id(self, zone_id: str) -> Optional[DNSZone]:
        """Return a zone by its id, or None."""

    @abstractmethod
    def _create_zone(self, domain: str) -> DNSZone:
        """Create a public zone for a domain."""

    @abstractmethod
    def _delete_zone(self, zone: DNSZone) -> None:
        """Delete a zone, and its records."""

    @abstractmethod
    def _list_records(self, zone_id: str) -> list[DNSRecord]:
        """Return a zone's records."""

    @abstractmethod
    def _upsert_record(self, zone_id: str, record: DNSRecord, create: bool) -> None:
        """Create a record, or replace the record of the same name and type."""

    @abstractmethod
    def _delete_record(self, zone_id: str, record: DNSRecord) -> None:
        """Delete a record, as :meth:`_list_records` returned it."""

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    # --------------------------------------------------------------------------
    # domains
    # --------------------------------------------------------------------------
    @property
    def environment_api_domain(self) -> str:
        """
        The environment's API domain, as it exists in DNS, e.g. ``local.api.example.com``.

        In the local environment, ``smarter_settings.environment_api_domain`` is a localhost
        domain, which DNS cannot serve, so this is its proxy domain.
        """
        return f"{smarter_settings.environment}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}"

    def _proxy_domain(self, domain: str) -> str:
        """In the local environment, replace the environment's API domain with its proxy domain."""
        if (
            smarter_settings.environment == SmarterEnvironments.LOCAL
            and smarter_settings.environment_api_domain in domain
        ):
            proxy_domain = domain.replace(smarter_settings.environment_api_domain, self.environment_api_domain)
            logger.debug("%s replacing %s with proxy domain %s", self.formatted_class_name, domain, proxy_domain)
            return proxy_domain
        return domain

    def _refuse_local_host(self, domain: str) -> None:
        host = urlparse(f"http://{domain}").netloc
        if host in smarter_settings.local_hosts:
            raise SmarterValueError(f"Domain {host} is prohibited.")

    def resolve_domain(self, domain: str) -> str:
        """
        Validate a domain, and replace a local environment's API domain with its proxy domain.

        :param domain: A domain, e.g. ``example.api.localhost:9357``.
        :returns: The domain as it exists in DNS.
        :raises SmarterValueError: If the domain is invalid, or is a local host.
        """
        resolved = self._proxy_domain(domain)
        if resolved == domain:
            # catch-all to ensure that we never work with a local host.
            self._refuse_local_host(domain)
        SmarterValidator.validate_domain(domain)
        return resolved

    def resolve_record_name(self, name: str) -> str:
        """
        Resolve a record's name, as :meth:`resolve_domain` does, but without validating it as a host name.

        Record names may contain labels that host names may not, e.g. ``_acme-challenge.example.com``.
        """
        name = normalize_name(name)
        resolved = self._proxy_domain(name)
        if resolved == name:
            self._refuse_local_host(name)
        return normalize_name(resolved)

    # --------------------------------------------------------------------------
    # zones
    # --------------------------------------------------------------------------
    def get_zone(self, domain: str) -> Optional[DNSZone]:
        """
        Return the zone of a domain.

        :param domain: The zone's domain, e.g. ``example.com``.
        :returns: The zone, or None if it does not exist.
        """
        self.require_ready()
        domain = self.resolve_domain(domain)
        with self.operation("get_zone"):
            return self._find_zone(normalize_name(domain))

    def get_zone_by_id(self, zone_id: str) -> Optional[DNSZone]:
        """
        Return a zone by its id.

        :param zone_id: The provider's id of the zone.
        :returns: The zone, with its name servers, or None if it does not exist.
        """
        self.require_ready()
        with self.operation("get_zone_by_id"):
            return self._find_zone_by_id(zone_id)

    def get_or_create_zone(self, domain: str) -> tuple[DNSZone, bool]:
        """
        Return the zone of a domain, and create it if it does not exist.

        A new zone is billable in most clouds, so it is announced with
        :data:`~smarter.apps.infrastructure.signals.billable_resource_creating` and
        :data:`~smarter.apps.infrastructure.signals.billable_resource_created`.

        :param domain: The zone's domain, e.g. ``example.com``.
        :returns: The zone, and whether it was created.
        """
        zone = self.get_zone(domain)
        if zone is not None:
            return zone, False
        domain = normalize_name(self.resolve_domain(domain))
        resource = self.creating_resource(RESOURCE_TYPE_ZONE, domain, billable=self.billable_zones)
        with self.operation("create_zone"):
            zone = self._create_zone(domain)
        self.created_resource(resource, resource_id=zone.id)
        logger.info("%s created DNS zone %s %s", self.formatted_class_name, zone.name, zone.id)
        return zone, True

    def delete_zone(self, domain: str) -> bool:
        """
        Delete the zone of a domain, and all of its records.

        This cannot be undone.

        :param domain: The zone's domain.
        :returns: True if the zone was deleted, False if it did not exist.
        """
        zone = self.get_zone(domain)
        if zone is None:
            return False
        resource = self.destroying_resource(RESOURCE_TYPE_ZONE, zone.name, zone.id, billable=self.billable_zones)
        with self.operation("delete_zone"):
            self._delete_zone(zone)
        self.destroyed_resource(resource)
        return True

    def get_name_servers(self, zone_id: str) -> list[str]:
        """
        Return the name servers of a zone, e.g. for a customer to delegate their domain to.

        :param zone_id: The provider's id of the zone.
        :returns: The name servers, without trailing dots.
        :raises DNSZoneNotFound: If the zone does not exist.
        """
        zone = self.get_zone_by_id(zone_id)
        if zone is None:
            raise DNSZoneNotFound(f"DNS zone {zone_id} does not exist.")
        return list(zone.name_servers)

    # --------------------------------------------------------------------------
    # records
    # --------------------------------------------------------------------------
    def list_records(self, zone_id: str) -> list[DNSRecord]:
        """Return a zone's records."""
        self.require_ready()
        with self.operation("list_records"):
            return self._list_records(zone_id)

    def get_record(self, zone_id: str, name: str, record_type: str) -> Optional[DNSRecord]:
        """
        Return a record of a zone.

        :param zone_id: The provider's id of the zone.
        :param name: The record's name, e.g. ``api.example.com``.
        :param record_type: The record's type, e.g. ``A``.
        :returns: The record, or None if it does not exist.
        """
        name = self.resolve_record_name(name)
        record_type = record_type.upper()
        for record in self.list_records(zone_id):
            if record.name == name and record.type == record_type:
                return record
        return None

    # pylint: disable=too-many-arguments
    def get_or_create_record(
        self,
        zone_id: str,
        name: str,
        record_type: str,
        ttl: Optional[int] = DEFAULT_DNS_RECORD_TTL,
        values: Optional[list[str]] = None,
        alias: Optional[dict[str, Any]] = None,
    ) -> tuple[DNSRecord, bool]:
        """
        Return a record, and create it, or update its values, if it does not match.

        :param zone_id: The provider's id of the zone.
        :param name: The record's name.
        :param record_type: The record's type.
        :param ttl: Seconds. Ignored for an alias record.
        :param values: The record's values, e.g. IP addresses.
        :param alias: A provider-specific alias target, in place of values.
        :returns: The record, and whether it was created, rather than found or updated.
        :raises DNSRecordTimeout: If the record does not appear in the zone in time.
        """
        wanted = DNSRecord(
            name=self.resolve_record_name(name),
            type=record_type,
            ttl=None if alias else ttl,
            values=list(values or []),
            alias=alias,
        )
        existing = self.get_record(zone_id, wanted.name, wanted.type)
        if existing is not None and existing.same_target(wanted):
            return existing, False

        create = existing is None
        resource = self.creating_resource(RESOURCE_TYPE_RECORD, f"{wanted.name} {wanted.type}")
        with self.operation("upsert_record"):
            self._upsert_record(zone_id, wanted, create=create)

        for attempt in range(1, self.record_wait_attempts + 1):
            record = self.get_record(zone_id, wanted.name, wanted.type)
            if record is not None:
                self.created_resource(resource, resource_id=zone_id)
                return record, create
            if attempt < self.record_wait_attempts:
                logger.debug(
                    "%s waiting %s seconds for %s %s, attempt %s of %s",
                    self.formatted_class_name,
                    self.record_wait_seconds,
                    wanted.name,
                    wanted.type,
                    attempt,
                    self.record_wait_attempts,
                )
                self._sleep(self.record_wait_seconds)
        raise DNSRecordTimeout(
            f"DNS record {wanted.name} {wanted.type} did not appear in zone {zone_id} "
            f"after {self.record_wait_attempts} attempts."
        )

    def delete_record(self, zone_id: str, name: str, record_type: str) -> bool:
        """
        Delete a record.

        :param zone_id: The provider's id of the zone.
        :param name: The record's name.
        :param record_type: The record's type.
        :returns: True if the record was deleted, False if it did not exist.
        """
        record = self.get_record(zone_id, name, record_type)
        if record is None:
            return False
        resource = self.destroying_resource(RESOURCE_TYPE_RECORD, f"{record.name} {record.type}", zone_id)
        with self.operation("delete_record"):
            self._delete_record(zone_id, record)
        self.destroyed_resource(resource)
        return True

    # --------------------------------------------------------------------------
    # the platform's records
    # --------------------------------------------------------------------------
    def get_environment_a_record(self, domain: Optional[str] = None) -> Optional[DNSRecord]:
        """
        Return the A record of a domain, in its own zone: by default, the environment's domain.

        The A record of a Smarter environment's domain points at its load balancer. The
        platform copies it to the hosts that it serves, e.g. each LLMClient's.

        :param domain: The domain, by default ``smarter_settings.environment_platform_domain``.
        :returns: The A record, or None if the domain has no zone or no A record.
        """
        domain = normalize_name(self.resolve_domain(domain or smarter_settings.environment_platform_domain))
        zone = self.get_zone(domain)
        if zone is None:
            return None
        return self.get_record(zone.id, domain, "A")

    def create_domain_a_record(
        self, hostname: str, api_host_domain: str, zone_id: Optional[str] = None
    ) -> tuple[DNSRecord, bool]:
        """
        Point a host at the same target as a parent domain, by copying the parent's A record.

        e.g. an LLMClient's host, ``example.3141-5926-5359.api.smarter.sh``, points at the load
        balancer of ``api.smarter.sh``.

        :param hostname: The host, e.g. ``example.3141-5926-5359.api.smarter.sh``.
        :param api_host_domain: The parent domain whose A record is copied, e.g. ``api.smarter.sh``.
            The record is created in its zone, unless ``zone_id`` is given.
        :param zone_id: The zone in which to create the record, e.g. a custom domain's.
        :returns: The record, and whether it was created.
        :raises DNSZoneNotFound: If the parent domain has no A record.
        """
        hostname = normalize_name(self.resolve_domain(hostname))
        api_host_domain = normalize_name(self.resolve_domain(api_host_domain))
        if not zone_id:
            zone, _ = self.get_or_create_zone(api_host_domain)
            zone_id = zone.id
        a_record = self.get_environment_a_record(api_host_domain)
        if a_record is None:
            raise DNSZoneNotFound(f"{api_host_domain} has no A record to copy to {hostname}.")
        logger.debug(
            "%s copying the A record of %s to %s in zone %s",
            self.formatted_class_name,
            api_host_domain,
            hostname,
            zone_id,
        )
        return self.get_or_create_record(
            zone_id=zone_id,
            name=hostname,
            record_type="A",
            ttl=smarter_settings.llmclient_tasks_default_ttl,
            values=a_record.values,
            alias=a_record.alias,
        )


__all__ = ["DNSRecord", "DNSService", "DNSZone", "normalize_name"]
