"""Exceptions of the low-level AWS helpers."""

from smarter.apps.infrastructure.exceptions import (
    InfrastructureNotReadyError,
    SmarterInfrastructureError,
)


class SmarterAWSError(SmarterInfrastructureError):
    """Base class for AWS errors."""


class AWSNotReadyError(SmarterAWSError, InfrastructureNotReadyError):
    """Raised when the AWS client is not ready."""


__all__ = ["AWSNotReadyError", "SmarterAWSError"]
