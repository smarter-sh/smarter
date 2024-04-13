"""Custom exceptions for the AWS module."""


class AWSACMVerificationFailed(Exception):
    """Raised when the verification of an ACM certificate fails."""


class AWSACMVerificationTimeout(Exception):
    """Raised when the verification of an ACM certificate times out."""


class AWSACMVerificationNotFound(Exception):
    """Raised when the verification of an ACM certificate is not found."""


class AWSACMCertificateNotFound(Exception):
    """Raised when an ACM certificate is not found."""


class AWSRoute53RecordNotFound(Exception):
    """Raised when a Route53 record is not found."""


class AWSRoute53ZoneNotFound(Exception):
    """Raised when a Route53 zone is not found."""


class AWSRoute53HostedZoneAlreadyExists(Exception):
    """Raised when a Route53 zone already exists."""
