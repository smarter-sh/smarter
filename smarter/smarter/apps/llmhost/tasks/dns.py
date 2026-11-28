"""
The DNS records of LLMHosts' Ingresses, which the llmhost tasks create and delete.

An LLMHost whose Ingress has the hostname that Smarter chose, e.g. ``qwen.3141-5926-5359.api.example.com``, gets a
DNS A record, as an LLMClient does, when DNS records are enabled. :func:`create_dns_record` calls the DNS provider,
and so runs only in the infrastructure worker, in ``launch_llmhost``. :func:`destroy_dns_record` queues the LLMClient
app's ``destroy_domain_A_record`` task.
"""

from typing import Optional

from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.llmhost.models import LLMHost
from smarter.apps.llmhost.services import LLMHostService, LLMHostServiceError
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_HOST_LOGGING]
)


def managed_hostname(llmhost: LLMHost) -> Optional[str]:
    """The Ingress hostname, if Smarter chose it, and so manages its DNS record."""
    service = LLMHostService()
    try:
        spec = service.spec_of(llmhost)
    except LLMHostServiceError:
        return None
    if not spec.network.ingress or spec.network.hostname:
        return None
    return service.default_hostname(llmhost, service.base_name(llmhost))


def dns_enabled() -> bool:
    """Whether LLMHost tasks manage DNS records, like LLMClient tasks."""
    return bool(smarter_settings.app_llmclient_tasks_create_dns_record and infrastructure.dns.ready)


def create_dns_record(llmhost: LLMHost) -> None:
    """
    Create the DNS A record of the LLMHost's default Ingress hostname, if DNS is enabled.

    Calls the DNS provider, e.g. Route53. Errors are logged, not raised.

    :param llmhost: The LLMHost.
    """
    hostname = managed_hostname(llmhost)
    if not hostname or not dns_enabled():
        return
    try:
        infrastructure.dns.create_domain_a_record(
            hostname=hostname, api_host_domain=smarter_settings.environment_api_domain
        )
        logger.info("created the DNS record %s for %s", hostname, llmhost)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error(
            "failed to create the DNS record %s for %s: %s",
            hostname,
            llmhost,
            e,
        )


def destroy_dns_record(llmhost: LLMHost) -> None:
    """
    Queue the Celery task that deletes the DNS A record of the LLMHost's default Ingress hostname, if DNS is enabled.

    :param llmhost: The LLMHost.
    """
    hostname = managed_hostname(llmhost)
    if not hostname or not dns_enabled():
        return
    # pylint: disable=import-outside-toplevel
    from smarter.apps.llmclient.tasks.destroy_domain_a_record import (
        destroy_domain_A_record,
    )

    destroy_domain_A_record.delay(hostname=hostname, api_host_domain=smarter_settings.environment_api_domain)


__all__ = ["create_dns_record", "destroy_dns_record", "dns_enabled", "managed_hostname"]
