"""Exceptions of the LLMHost service layer."""

from smarter.apps.llmhost.exceptions import SmarterLLMHostException


class LLMHostServiceError(SmarterLLMHostException):
    """Base class of the LLMHost service layer's exceptions."""


class LLMHostConfigurationError(LLMHostServiceError):
    """The LLMHost's spec is invalid, or refers to something that does not exist, e.g. a Secret."""


class LLMHostClusterError(LLMHostServiceError):
    """The Kubernetes cluster is unavailable, or rejected the LLMHost's resources."""


class LLMHostComputeError(LLMHostServiceError):
    """An LLMHost does not fit its compute, or the compute's node group cannot be managed."""


class LLMHostDiscoveryError(LLMHostServiceError):
    """A model catalog is unavailable, or does not have the model."""
