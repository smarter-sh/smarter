"""Celery task exceptions for llm_client app."""

from smarter.apps.llm_client.exceptions import SmarterLLMClientException


class LLMClientCustomDomainNotFound(SmarterLLMClientException):
    """Raised when the custom domain for the llm_client is not found."""


class LLMClientCustomDomainExists(SmarterLLMClientException):
    """Raised when the custom domain for the llm_client already exists."""


class LLMClientTaskError(SmarterLLMClientException):
    """Base class for LLMClient task exceptions."""
