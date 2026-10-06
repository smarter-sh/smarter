"""
The certificate service: TLS certificates, issued by a cloud provider and validated with DNS.

The platform uses :class:`CertificateService`, through
:data:`smarter.apps.infrastructure.services.infrastructure` ``.certificates``, and the provider's
certificate authority is an implementation of it, e.g.
:class:`~smarter.apps.infrastructure.providers.aws.certificates.ACMCertificateService`.

A certificate is validated with DNS records, which the service creates with a
:class:`~smarter.apps.infrastructure.services.dns.DNSService`, normally its provider's, so that a
certificate authority and a DNS service of different providers can be combined.
"""

import time
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..const import CertificateStatus, InfrastructureServiceNames
from ..exceptions import (
    CertificateNotFound,
    CertificateServiceError,
    CertificateTimeout,
)
from .base import InfrastructureService
from .dns import DNSRecord, DNSService, normalize_name

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])

RESOURCE_TYPE_CERTIFICATE = "certificate"
VALIDATION_RECORD_TTL = 300


@dataclass
class Certificate:
    """A TLS certificate, for a domain and its subdomains."""

    id: str
    """The provider's id of the certificate, e.g. an AWS ACM certificate ARN."""

    domain_name: str
    """The certificate's domain, e.g. ``example.com``."""

    status: str
    """See :class:`~smarter.apps.infrastructure.const.CertificateStatus`."""

    validation_records: list[DNSRecord] = field(default_factory=list)
    """The DNS records that prove control of the domain, once the provider has generated them."""

    @property
    def is_issued(self) -> bool:
        return self.status == CertificateStatus.ISSUED


class CertificateService(InfrastructureService):
    """
    The TLS certificate service of a cloud provider.

    :param provider_name: The name of the provider, e.g. ``aws``.
    :param dns: The DNS service in which to create validation records.
    """

    service_name = InfrastructureServiceNames.CERTIFICATES
    error_class = CertificateServiceError

    billable_certificates: bool = False
    """Whether the provider bills for certificates.

    AWS ACM's public certificates are free.
    """

    validation_wait_attempts: int = 120
    """How many times to look for a new certificate's validation records, before :class:`CertificateTimeout`."""

    validation_wait_seconds: float = 5
    """Seconds between the attempts.

    A provider generates validation records in seconds.
    """

    issue_wait_attempts: int = 20
    """How many times :meth:`wait_until_issued` checks the certificate."""

    issue_wait_seconds: float = 30
    """Seconds between the checks."""

    def __init__(self, provider_name: str, dns: DNSService, *args, **kwargs):
        super().__init__(provider_name, *args, **kwargs)
        self.dns = dns

    # --------------------------------------------------------------------------
    # primitives, which a provider implements
    # --------------------------------------------------------------------------
    @abstractmethod
    def _find_certificate_id(self, domain_name: str) -> Optional[str]:
        """Return the id of a domain's certificate, or None."""

    @abstractmethod
    def _request_certificate(self, domain_name: str) -> str:
        """Request a DNS-validated certificate for a domain and its subdomains, and return its id."""

    @abstractmethod
    def _describe_certificate(self, certificate_id: str) -> Optional[Certificate]:
        """Return a certificate, or None if it does not exist."""

    @abstractmethod
    def _delete_certificate(self, certificate_id: str) -> None:
        """Delete a certificate."""

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    # --------------------------------------------------------------------------
    # operations
    # --------------------------------------------------------------------------
    def get_certificate_id(self, domain_name: str) -> Optional[str]:
        """
        Return the id of a domain's certificate.

        :param domain_name: The certificate's domain, e.g. ``example.com``.
        :returns: The id, or None if the domain has no certificate.
        """
        self.require_ready()
        with self.operation("get_certificate_id"):
            return self._find_certificate_id(domain_name)

    def get_certificate(self, certificate_id: str) -> Certificate:
        """
        Return a certificate.

        :param certificate_id: The provider's id of the certificate.
        :raises CertificateNotFound: If the certificate does not exist.
        """
        self.require_ready()
        with self.operation("get_certificate"):
            certificate = self._describe_certificate(certificate_id)
        if certificate is None:
            raise CertificateNotFound(f"Certificate {certificate_id} does not exist.")
        return certificate

    def get_or_create_certificate(self, domain_name: str) -> tuple[str, bool]:
        """
        Return the id of a domain's certificate, and request one if it has none.

        The certificate covers the domain and its subdomains, e.g. ``example.com`` and
        ``*.example.com``. It is not issued until its validation records exist, see
        :meth:`create_validation_records`.

        :param domain_name: The certificate's domain.
        :returns: The certificate's id, and whether it was requested.
        """
        certificate_id = self.get_certificate_id(domain_name)
        if certificate_id:
            return certificate_id, False
        resource = self.creating_resource(
            RESOURCE_TYPE_CERTIFICATE, normalize_name(domain_name), billable=self.billable_certificates
        )
        with self.operation("request_certificate"):
            certificate_id = self._request_certificate(domain_name)
        self.created_resource(resource, resource_id=certificate_id)
        return certificate_id, True

    def wait_for_validation_records(self, certificate_id: str) -> Certificate:
        """
        Return a certificate once its provider has generated its validation records.

        :param certificate_id: The provider's id of the certificate.
        :raises CertificateTimeout: If the records are not generated in time.
        :raises CertificateNotFound: If the certificate does not exist, after the last attempt.
        """
        for attempt in range(1, self.validation_wait_attempts + 1):
            try:
                certificate = self.get_certificate(certificate_id)
                if certificate.validation_records:
                    return certificate
            except CertificateNotFound:
                # a new certificate can take a few seconds to exist.
                if attempt >= self.validation_wait_attempts:
                    raise
            if attempt < self.validation_wait_attempts:
                self._sleep(self.validation_wait_seconds)
        raise CertificateTimeout(f"Timed out waiting for the validation records of certificate {certificate_id}.")

    def create_validation_records(self, certificate_id: str) -> list[DNSRecord]:
        """
        Create the DNS records that validate a certificate, in its domain's zone.

        The zone is created if it does not exist. The provider can only read the records once
        the domain is delegated to the zone.

        :param certificate_id: The provider's id of the certificate.
        :returns: The validation records.
        """
        certificate = self.wait_for_validation_records(certificate_id)
        zone, _ = self.dns.get_or_create_zone(certificate.domain_name)
        records: list[DNSRecord] = []
        seen: set[tuple[str, str]] = set()
        for wanted in certificate.validation_records:
            # a domain and its wildcard share a validation record.
            if (wanted.name, wanted.type) in seen:
                continue
            seen.add((wanted.name, wanted.type))
            record, _ = self.dns.get_or_create_record(
                zone_id=zone.id,
                name=wanted.name,
                record_type=wanted.type,
                ttl=VALIDATION_RECORD_TTL,
                values=wanted.values,
            )
            records.append(record)
        return records

    def certificate_status(self, certificate_id: str) -> str:
        """
        Return a certificate's status, e.g. ``PENDING_VALIDATION`` or ``ISSUED``.

        See :class:`~smarter.apps.infrastructure.const.CertificateStatus`.
        """
        return self.get_certificate(certificate_id).status

    def is_issued(self, certificate_id: str) -> bool:
        """Whether a certificate is issued, i.e. its domain is validated."""
        return self.certificate_status(certificate_id) == CertificateStatus.ISSUED

    def wait_until_issued(self, certificate_id: str) -> bool:
        """
        Wait for a certificate to be issued.

        :param certificate_id: The provider's id of the certificate.
        :returns: True if it is issued, False if it is not after :attr:`issue_wait_attempts` checks.
        """
        for attempt in range(1, self.issue_wait_attempts + 1):
            if self.is_issued(certificate_id):
                return True
            if attempt < self.issue_wait_attempts:
                self._sleep(self.issue_wait_seconds)
        logger.error("%s certificate %s was not issued in time", self.formatted_class_name, certificate_id)
        return False

    def delete_certificate(self, certificate_id: str) -> bool:
        """
        Delete a certificate.

        :param certificate_id: The provider's id of the certificate.
        :returns: True if it was deleted, False if it did not exist.
        """
        self.require_ready()
        with self.operation("get_certificate"):
            certificate = self._describe_certificate(certificate_id)
        if certificate is None:
            return False
        resource = self.destroying_resource(
            RESOURCE_TYPE_CERTIFICATE, certificate.domain_name, certificate_id, billable=self.billable_certificates
        )
        with self.operation("delete_certificate"):
            self._delete_certificate(certificate_id)
        self.destroyed_resource(resource)
        return True


__all__ = ["Certificate", "CertificateService"]
