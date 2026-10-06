"""
The low-level AWS Route53 helper.

It wraps the boto3 Route53 client for
:class:`~smarter.apps.infrastructure.providers.aws.dns.Route53DNSService`, which implements the
platform's DNS service with it. The DNS operations themselves, e.g. copying an A record to a
new host, are provider-independent, in :class:`~smarter.apps.infrastructure.services.dns.DNSService`.
"""

# python stuff
import time
from typing import Any, Optional

from smarter.lib import logging

from .base import AWSBase
from .exceptions import AWSNotReadyError

logger = logging.getLogger(__name__)

HOSTED_ZONE_PREFIX = "/hostedzone/"


def hosted_zone_id(value: str) -> str:
    """The id of a hosted zone, without the ``/hostedzone/`` prefix of the Route53 API's ``Id``."""
    return str(value).split("/")[-1]


class AWSRoute53(AWSBase):
    """
    The AWS Route53 helper: hosted zones and their record sets.

    Names are compared without their trailing dot, which Route53 adds.
    """

    _client = None
    _client_type: str = "route53"

    @property
    def route53(self):
        """The boto3 Route53 client."""
        if not self.ready or not self.client:
            raise AWSNotReadyError(f"{self.formatted_class_name} is not ready to interact with AWS Route53.")
        return self.client

    def list_hosted_zones(self) -> list[dict[str, Any]]:
        """Return every hosted zone of the account."""
        zones: list[dict[str, Any]] = []
        for page in self.route53.get_paginator("list_hosted_zones").paginate():
            zones.extend(page["HostedZones"])
        return zones

    def get_hosted_zone(self, domain_name: str) -> Optional[dict[str, Any]]:
        """
        Return the hosted zone of a domain.

        :param domain_name: The domain, with or without a trailing dot.
        :returns: The hosted zone, as ``list_hosted_zones`` describes it, or None.
        """
        domain_name = domain_name.rstrip(".")
        for zone in self.list_hosted_zones():
            if zone["Name"].rstrip(".") == domain_name:
                return zone
        return None

    def get_hosted_zone_by_id(self, zone_id: str) -> Optional[dict[str, Any]]:
        """
        Return a hosted zone, and its delegation set, by its id.

        Example return value:

        .. code-block:: json

            {
                "HostedZone": {"Id": "/hostedzone/Z148QEXAMPLE8V", "Name": "example.com."},
                "DelegationSet": {"NameServers": ["ns-2048.awsdns-64.com", "ns-2049.awsdns-65.net"]}
            }

        :param zone_id: The hosted zone's id, with or without the ``/hostedzone/`` prefix.
        :returns: The hosted zone, or None if it does not exist.
        """
        try:
            return self.route53.get_hosted_zone(Id=hosted_zone_id(zone_id))
        except self.route53.exceptions.NoSuchHostedZone:
            return None

    def create_hosted_zone(self, domain_name: str) -> dict[str, Any]:
        """
        Create a public hosted zone.

        :returns: The response of ``create_hosted_zone``: the ``HostedZone``, and its ``DelegationSet``.
        """
        return self.route53.create_hosted_zone(
            Name=domain_name,
            CallerReference=str(time.time()),  # Unique string used to identify the request
            HostedZoneConfig={"Comment": "Managed by Smarter", "PrivateZone": False},
        )

    def list_record_sets(self, zone_id: str) -> list[dict[str, Any]]:
        """Return every record set of a hosted zone."""
        record_sets: list[dict[str, Any]] = []
        paginator = self.route53.get_paginator("list_resource_record_sets")
        for page in paginator.paginate(HostedZoneId=hosted_zone_id(zone_id)):
            record_sets.extend(page["ResourceRecordSets"])
        return record_sets

    def change_record_set(self, zone_id: str, action: str, record_set: dict[str, Any]) -> None:
        """
        Change one record set.

        :param zone_id: The hosted zone's id.
        :param action: ``CREATE``, ``UPSERT`` or ``DELETE``.
        :param record_set: The ``ResourceRecordSet``. To delete one, it must match the existing one.
        """
        logger.debug("%s.change_record_set() %s %s %s", self.formatted_class_name, zone_id, action, record_set)
        self.route53.change_resource_record_sets(
            HostedZoneId=hosted_zone_id(zone_id),
            ChangeBatch={"Changes": [{"Action": action, "ResourceRecordSet": record_set}]},
        )

    def delete_hosted_zone(self, zone_id: str) -> None:
        """
        Delete a hosted zone, and its record sets.

        Route53 manages a zone's NS and SOA records, which are deleted with the zone.
        """
        for record_set in self.list_record_sets(zone_id):
            if record_set["Type"] not in ("NS", "SOA"):
                self.change_record_set(zone_id, "DELETE", record_set)
        self.route53.delete_hosted_zone(Id=hosted_zone_id(zone_id))


__all__ = ["AWSRoute53", "hosted_zone_id"]
