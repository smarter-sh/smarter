"""Custom exceptions for the AWS module."""

from smarter.common.exceptions import SmarterExceptionBase


class AWSNotReadyError(SmarterExceptionBase):
    """Raised when the AWS client is not ready."""


class AWSACMVerificationFailed(SmarterExceptionBase):
    """Raised when the verification of an ACM certificate fails."""


class AWSACMVerificationTimeout(SmarterExceptionBase):
    """Raised when the verification of an ACM certificate times out."""


class AWSRoute53RecordVerificationTimeout(SmarterExceptionBase):
    """Raised when the verification of a Route53 record times out."""


class AWSACMVerificationNotFound(SmarterExceptionBase):
    """Raised when the verification of an ACM certificate is not found."""


class AWSACMCertificateNotFound(SmarterExceptionBase):
    """Raised when an ACM certificate is not found."""


class AWSRoute53RecordNotFound(SmarterExceptionBase):
    """Raised when a Route53 record is not found."""


class AWSRoute53ZoneNotFound(SmarterExceptionBase):
    """Raised when a Route53 zone is not found."""


class AWSRoute53HostedZoneAlreadyExists(SmarterExceptionBase):
    """Raised when a Route53 zone already exists."""
