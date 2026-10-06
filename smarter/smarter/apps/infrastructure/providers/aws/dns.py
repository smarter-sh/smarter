"""
The DNS service of AWS: Route53.

:class:`Route53DNSService` implements the primitives of
:class:`~smarter.apps.infrastructure.services.dns.DNSService` with the low-level
:class:`~smarter.apps.infrastructure.providers.aws.helpers.route53.AWSRoute53` helper, and
translates between Route53's hosted zones and record sets and the provider-independent
:class:`~smarter.apps.infrastructure.services.dns.DNSZone` and
:class:`~smarter.apps.infrastructure.services.dns.DNSRecord`.
"""

from typing import TYPE_CHECKING, Any, Optional

from ...services.dns import DNSRecord, DNSService, DNSZone
from .helpers.route53 import AWSRoute53, hosted_zone_id

if TYPE_CHECKING:
    from .provider import AWSProvider


def _unquote(value: str) -> str:
    return value[1:-1] if len(value) >= 2 and value.startswith('"') and value.endswith('"') else value


def to_record(record_set: dict[str, Any]) -> DNSRecord:
    """A Route53 record set as a :class:`DNSRecord`.

    TXT values are unquoted.
    """
    record_type = str(record_set["Type"]).upper()
    values = [str(item["Value"]) for item in record_set.get("ResourceRecords", []) if "Value" in item]
    if record_type == "TXT":
        values = [_unquote(value) for value in values]
    return DNSRecord(
        name=record_set["Name"],
        type=record_type,
        ttl=record_set.get("TTL"),
        values=values,
        alias=record_set.get("AliasTarget"),
    )


def to_record_set(record: DNSRecord) -> dict[str, Any]:
    """A :class:`DNSRecord` as a Route53 record set.

    TXT values are quoted, as Route53 requires.
    """
    record_set: dict[str, Any] = {"Name": record.name, "Type": record.type}
    if record.alias:
        record_set["AliasTarget"] = record.alias
        return record_set
    values = record.values
    if record.type == "TXT":
        values = [value if value.startswith('"') else f'"{value}"' for value in values]
    record_set["TTL"] = record.ttl
    record_set["ResourceRecords"] = [{"Value": value} for value in values]
    return record_set


def to_zone(hosted_zone: dict[str, Any], delegation_set: Optional[dict[str, Any]] = None) -> DNSZone:
    """A Route53 hosted zone, and optionally its delegation set, as a :class:`DNSZone`."""
    return DNSZone(
        id=hosted_zone_id(hosted_zone["Id"]),
        name=hosted_zone["Name"],
        name_servers=list((delegation_set or {}).get("NameServers", [])),
    )


class Route53DNSService(DNSService):
    """
    AWS Route53, as the platform's DNS.

    :param provider: The AWS provider, which authenticates with AWS.
    """

    def __init__(self, provider: "AWSProvider", **kwargs):
        super().__init__(provider_name=provider.provider_name, **kwargs)
        self.provider = provider
        self._route53: Optional[AWSRoute53] = None

    @property
    def ready(self) -> bool:
        return self.provider.ready

    @property
    def route53(self) -> AWSRoute53:
        """The low-level Route53 helper, created when it is first used."""
        if self._route53 is None:
            self.provider.require_live()
            self._route53 = AWSRoute53()
            self.connection_state(True)
        return self._route53

    def _find_zone(self, domain: str) -> Optional[DNSZone]:
        hosted_zone = self.route53.get_hosted_zone(domain)
        return to_zone(hosted_zone) if hosted_zone else None

    def _find_zone_by_id(self, zone_id: str) -> Optional[DNSZone]:
        response = self.route53.get_hosted_zone_by_id(zone_id)
        if not response:
            return None
        return to_zone(response["HostedZone"], response.get("DelegationSet"))

    def _create_zone(self, domain: str) -> DNSZone:
        response = self.route53.create_hosted_zone(domain)
        return to_zone(response["HostedZone"], response.get("DelegationSet"))

    def _delete_zone(self, zone: DNSZone) -> None:
        self.route53.delete_hosted_zone(zone.id)

    def _list_records(self, zone_id: str) -> list[DNSRecord]:
        return [to_record(record_set) for record_set in self.route53.list_record_sets(zone_id)]

    def _upsert_record(self, zone_id: str, record: DNSRecord, create: bool) -> None:
        self.route53.change_record_set(zone_id, "CREATE" if create else "UPSERT", to_record_set(record))

    def _delete_record(self, zone_id: str, record: DNSRecord) -> None:
        self.route53.change_record_set(zone_id, "DELETE", to_record_set(record))


__all__ = ["Route53DNSService", "to_record", "to_record_set", "to_zone"]
