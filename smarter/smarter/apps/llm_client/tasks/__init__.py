"""Celery tasks for llm_client app."""

from .aggregate_llm_client_history import aggregate_llm_client_history
from .create_custom_domain_dns_record import create_custom_domain_dns_record
from .create_llm_client_request import create_llm_client_request
from .delete_default_api import delete_default_api
from .deploy_custom_api import deploy_custom_api
from .deploy_default_api import deploy_default_api
from .destroy_domain_a_record import destroy_domain_A_record
from .exceptions import (
    LLMClientCustomDomainExists,
    LLMClientCustomDomainNotFound,
    LLMClientTaskError,
)
from .register_custom_domain import register_custom_domain
from .undeploy_default_api import undeploy_default_api
from .utils import is_taskable
from .verify_certificate import verify_certificate
from .verify_custom_domain import verify_custom_domain
from .verify_domain import verify_domain

__all__ = [
    "aggregate_llm_client_history",
    "create_llm_client_request",
    "create_custom_domain_dns_record",
    "delete_default_api",
    "deploy_custom_api",
    "deploy_default_api",
    "destroy_domain_A_record",
    "register_custom_domain",
    "undeploy_default_api",
    "verify_certificate",
    "verify_custom_domain",
    "verify_domain",
    "LLMClientCustomDomainExists",
    "LLMClientCustomDomainNotFound",
    "LLMClientTaskError",
    "is_taskable",
]
