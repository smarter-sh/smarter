"""
The low-level AWS Certificate Manager (ACM) helper.

It wraps the boto3 ACM client for
:class:`~smarter.apps.infrastructure.providers.aws.certificates.ACMCertificateService`, which
implements the platform's certificate service with it. Waiting for validation records, and
creating them in DNS, are provider-independent, in
:class:`~smarter.apps.infrastructure.services.certificates.CertificateService`.

See ``tests/data/acm_certificate_detail.json`` of the infrastructure app for an example of a
certificate's description.
"""

from typing import Any, Optional

from smarter.lib import logging

from .base import AWSBase
from .exceptions import AWSNotReadyError

logger = logging.getLogger(__name__)


class AWSCertificateManager(AWSBase):
    """The AWS Certificate Manager helper: DNS-validated public certificates."""

    _client = None
    _client_type: str = "acm"

    @property
    def acm(self):
        """The boto3 ACM client."""
        if not self.ready or not self.client:
            raise AWSNotReadyError(f"{self.formatted_class_name} is not ready to interact with AWS ACM.")
        return self.client

    def get_certificate_arn(self, domain_name: str) -> Optional[str]:
        """
        Return the ARN of a domain's certificate.

        :param domain_name: The certificate's domain.
        :returns: The ARN, or None if the domain has no certificate.
        """
        for page in self.acm.get_paginator("list_certificates").paginate():
            for certificate in page["CertificateSummaryList"]:
                if certificate["DomainName"] == domain_name:
                    return certificate["CertificateArn"]
        return None

    def request_certificate(self, domain_name: str) -> str:
        """
        Request a DNS-validated certificate for a domain and its subdomains.

        :returns: The certificate's ARN.
        """
        response = self.acm.request_certificate(
            DomainName=domain_name,
            ValidationMethod="DNS",
            SubjectAlternativeNames=[f"*.{domain_name}"],
        )
        return response["CertificateArn"]

    def describe_certificate(self, certificate_arn: str) -> Optional[dict[str, Any]]:
        """
        Return a certificate's description: its ``Certificate``.

        :returns: The description, or None if the certificate does not exist.
        """
        try:
            return self.acm.describe_certificate(CertificateArn=certificate_arn)["Certificate"]
        except self.acm.exceptions.ResourceNotFoundException:
            return None

    def delete_certificate(self, certificate_arn: str) -> None:
        """Delete a certificate.

        A certificate that does not exist counts as deleted.
        """
        try:
            self.acm.delete_certificate(CertificateArn=certificate_arn)
        except self.acm.exceptions.ResourceNotFoundException:
            pass


__all__ = ["AWSCertificateManager"]
