"""
The certificate service of AWS: AWS Certificate Manager (ACM).

:class:`ACMCertificateService` implements the primitives of
:class:`~smarter.apps.infrastructure.services.certificates.CertificateService` with the
low-level :class:`~smarter.apps.infrastructure.providers.aws.helpers.acm.AWSCertificateManager`
helper. A certificate's id is its ARN.
"""

from typing import TYPE_CHECKING, Any, Optional

from ...services.certificates import Certificate, CertificateService
from ...services.dns import DNSRecord, DNSService
from .helpers.acm import AWSCertificateManager

if TYPE_CHECKING:
    from .provider import AWSProvider


def to_certificate(description: dict[str, Any]) -> Certificate:
    """An ACM certificate's description as a :class:`Certificate`."""
    records = [
        DNSRecord(
            name=option["ResourceRecord"]["Name"],
            type=option["ResourceRecord"]["Type"],
            values=[option["ResourceRecord"]["Value"]],
        )
        for option in description.get("DomainValidationOptions", [])
        if option.get("ResourceRecord")
    ]
    return Certificate(
        id=description["CertificateArn"],
        domain_name=description["DomainName"],
        status=description.get("Status", ""),
        validation_records=records,
    )


class ACMCertificateService(CertificateService):
    """
    AWS Certificate Manager, as the platform's certificate authority.

    :param provider: The AWS provider, which authenticates with AWS.
    :param dns: The DNS service of the validation records.
    """

    def __init__(self, provider: "AWSProvider", dns: DNSService, **kwargs):
        super().__init__(provider.provider_name, dns, **kwargs)
        self.provider = provider
        self._acm: Optional[AWSCertificateManager] = None

    @property
    def ready(self) -> bool:
        return self.provider.ready

    @property
    def acm(self) -> AWSCertificateManager:
        """The low-level ACM helper, created when it is first used."""
        if self._acm is None:
            self.provider.require_live()
            self._acm = AWSCertificateManager()
            self.connection_state(True)
        return self._acm

    def _find_certificate_id(self, domain_name: str) -> Optional[str]:
        return self.acm.get_certificate_arn(domain_name)

    def _request_certificate(self, domain_name: str) -> str:
        return self.acm.request_certificate(domain_name)

    def _describe_certificate(self, certificate_id: str) -> Optional[Certificate]:
        description = self.acm.describe_certificate(certificate_id)
        return to_certificate(description) if description else None

    def _delete_certificate(self, certificate_id: str) -> None:
        self.acm.delete_certificate(certificate_id)


__all__ = ["ACMCertificateService", "to_certificate"]
