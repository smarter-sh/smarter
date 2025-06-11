"""Custom exceptions for the AWS module."""

from smarter.common.exceptions import SmarterException


class SmarterAWSError(SmarterException):
    """Base class for AWS errors."""


class AWSNotReadyError(SmarterAWSError):
    """Raised when the AWS client is not ready."""


class AWSACMVerificationFailed(SmarterAWSError):
    """Raised when the verification of an ACM certificate fails."""


class AWSACMVerificationTimeout(SmarterAWSError):
    """Raised when the verification of an ACM certificate times out."""


class AWSRoute53RecordVerificationTimeout(SmarterAWSError):
    """Raised when the verification of a Route53 record times out."""


class AWSACMVerificationNotFound(SmarterAWSError):
    """Raised when the verification of an ACM certificate is not found."""


class AWSACMCertificateNotFound(SmarterAWSError):
    """Raised when an ACM certificate is not found."""


class AWSRoute53RecordNotFound(SmarterAWSError):
    """Raised when a Route53 record is not found."""


class AWSRoute53ZoneNotFound(SmarterAWSError):
    """Raised when a Route53 zone is not found."""


class AWSRoute53HostedZoneAlreadyExists(SmarterAWSError):
    """Raised when a Route53 zone already exists."""
