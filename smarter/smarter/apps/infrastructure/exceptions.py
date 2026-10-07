"""
Exceptions of the infrastructure app.

The platform catches these, never a cloud provider's own exceptions: each provider translates
its SDK's errors into them.
"""

from smarter.common.exceptions import SmarterException


class SmarterInfrastructureError(SmarterException):
    """Base class of the infrastructure app's exceptions."""


class InfrastructureConfigurationError(SmarterInfrastructureError):
    """
    An infrastructure service is misconfigured, or is refused in the unit tests.

    The real cloud and cluster credentials of the Smarter containers can create billable
    resources, so the real services refuse to run in the unit tests unless they are asked to.
    """


class InfrastructureNotReadyError(SmarterInfrastructureError):
    """An infrastructure service is not authenticated, or not connected."""


class InfrastructureResourceNotFound(SmarterInfrastructureError):
    """An infrastructure resource, e.g. a DNS zone or a certificate, does not exist."""


class InfrastructureTimeout(SmarterInfrastructureError):
    """An infrastructure resource did not reach the expected state in time."""


class DNSServiceError(SmarterInfrastructureError):
    """The DNS service failed."""


class DNSZoneNotFound(DNSServiceError, InfrastructureResourceNotFound):
    """A DNS zone does not exist."""


class DNSRecordTimeout(DNSServiceError, InfrastructureTimeout):
    """A DNS record did not appear in its zone in time."""


class CertificateServiceError(SmarterInfrastructureError):
    """The certificate service failed."""


class CertificateNotFound(CertificateServiceError, InfrastructureResourceNotFound):
    """A certificate does not exist."""


class CertificateNotIssued(CertificateServiceError):
    """A certificate exists, but is not issued."""


class CertificateTimeout(CertificateServiceError, InfrastructureTimeout):
    """A certificate was not issued, or its validation records were not generated, in time."""


class KubernetesServiceError(SmarterInfrastructureError):
    """The Kubernetes cluster is unavailable, or rejected a request."""


class EmailServiceError(SmarterInfrastructureError):
    """The email service is misconfigured."""


__all__ = [
    "CertificateNotFound",
    "CertificateNotIssued",
    "CertificateServiceError",
    "CertificateTimeout",
    "DNSRecordTimeout",
    "DNSServiceError",
    "DNSZoneNotFound",
    "EmailServiceError",
    "InfrastructureConfigurationError",
    "InfrastructureNotReadyError",
    "InfrastructureResourceNotFound",
    "InfrastructureTimeout",
    "KubernetesServiceError",
    "SmarterInfrastructureError",
]
