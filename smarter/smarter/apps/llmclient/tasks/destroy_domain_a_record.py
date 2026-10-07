"""
Celery tasks for destroying llmclient domain A records.

This module defines tasks for destroying A records in the cloud provider's DNS for llmclient domains, including signal handling and logging.

Main Tasks
----------

- destroy_domain_A_record(hostname, api_host_domain):
    Destroys the A record for a given domain name in the cloud provider's DNS.

Signals
-------

- pre_destroy_domain_A_record: Sent before the A record is destroyed.
- post_destroy_domain_A_record: Sent after the A record is destroyed.

Configuration
-------------

Task behavior and logging are controlled by `smarter_settings` and waffle switches.

Logging
-------

Task execution and resource destruction are logged using the smarter logging library.

Usage
-----

Queue the Celery task, or call it directly to run it synchronously:

    destroy_domain_A_record.delay(hostname, api_host_domain)
    destroy_domain_A_record(hostname, api_host_domain)

Raises
------

Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from typing import Optional

from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.llmclient.signals import (
    post_destroy_domain_A_record,
    pre_destroy_domain_A_record,
)
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .utils import is_taskable

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.infrastructure_tasks_celery_task_queue,
)
def destroy_domain_A_record(hostname: str, api_host_domain: str, task_id: Optional[str] = None):
    """
    Destroy the A record for a given domain name in the cloud provider's DNS.

    A Celery task, e.g. ``destroy_domain_A_record.delay(...)``, which can also be called directly, to
    run synchronously, as delete_default_api does. This function locates the DNS zone of the specified parent domain, and deletes the A record of the given
    hostname from it. It sends pre- and post-destroy signals and logs all actions.

    Parameters
    ----------
    hostname : str
        The domain name whose A record should be destroyed.
    api_host_domain : str
        The parent domain used to locate the DNS zone.

    Signals
    -------
    pre_destroy_domain_A_record : django.dispatch.Signal
        Sent before the A record is destroyed.
    post_destroy_domain_A_record : django.dispatch.Signal
        Sent after the A record is destroyed.

    Returns
    -------
    None

    Raises
    ------
    Exception
        Any exception raised during the destruction process will be logged and may be handled by the caller.
    """
    if not is_taskable():
        return

    pre_destroy_domain_A_record.send(
        sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain, task_id=task_id
    )

    fn_name = logger_prefix + ".destroy_domain_A_record()"
    dns = infrastructure.dns
    hostname = dns.resolve_domain(hostname)
    api_host_domain = dns.resolve_domain(api_host_domain)
    logger.info("%s - %s task_id: %s", fn_name, hostname, task_id)

    # locate the DNS zone of the customer API domain. If it doesn't exist, neither does the record.
    zone = dns.get_zone(api_host_domain)
    if zone is None:
        logger.error(
            "%s DNS zone not found for %s. Nothing to do, returning. task_id: %s", fn_name, api_host_domain, task_id
        )
    elif dns.delete_record(zone.id, hostname, "A"):
        logger.info("%s deleted the A record of %s from zone %s task_id: %s", fn_name, hostname, zone.id, task_id)
    else:
        logger.error("%s A record not found for %s. Nothing to do, returning. task_id: %s", fn_name, hostname, task_id)
    post_destroy_domain_A_record.send(
        sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain, task_id=task_id
    )
