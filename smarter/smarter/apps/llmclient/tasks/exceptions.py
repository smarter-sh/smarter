"""Celery task exceptions for llmclient app."""

from smarter.apps.llmclient.exceptions import SmarterLLMClientException


class LLMClientCustomDomainNotFound(SmarterLLMClientException):
    """Raised when the custom domain for the llmclient is not found."""


class LLMClientCustomDomainExists(SmarterLLMClientException):
    """Raised when the custom domain for the llmclient already exists."""


class LLMClientTaskError(SmarterLLMClientException):
    """Base class for LLMClient task exceptions."""
