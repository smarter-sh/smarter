"""
Celery tasks for verifying llmclient domain DNS records.

This module defines Celery tasks for verifying that Internet domain names resolve to the expected DNS records (NS or other),
including signal handling, llmclient deployment status updates, and retry logic.

Main Tasks
----------

- verify_domain(domain_name, record_type="A", llmclient_id=None, activate_llmclient=False, hosted_zone_id=None, task_id=None, attempt=0):
    Attempts to verify that a domain name resolves to the expected DNS records, updating llmclient deployment status and sending verification signals.

A newly created DNS record can take hours to propagate. The task checks once, and if the domain
does not resolve yet, it schedules itself to check again in VERIFY_DOMAIN_INTERVAL seconds, up to
VERIFY_DOMAIN_MAX_ATTEMPTS times, rather than sleeping, so that it never blocks a Celery worker while
it waits. :func:`check_domain` is the single check, which deploy_default_api also uses.

Signals
-------

- pre_verify_domain: Sent before domain verification begins.
- post_verify_domain: Sent after domain verification is completed.
- llmclient_dns_verification_initiated: Sent when DNS verification is initiated.
- llmclient_dns_failed: Sent when DNS verification fails.
- llmclient_dns_verified: Sent when DNS verification succeeds.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`. The task runs in
the infrastructure queue, smarter_settings.infrastructure_tasks_celery_task_queue.

Logging
-------

Task execution, verification attempts, and results are logged using the smarter logging library, with waffle switches for task and llmclient logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously verify an llmclient domain:

    verify_domain.delay(domain_name, record_type, llmclient_id, activate_llmclient, hosted_zone_id, task_id)

Raises
------

Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from enum import Enum
from typing import Optional

import dns.resolver

from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.signals import (
    llmclient_dns_failed,
    llmclient_dns_verification_initiated,
    llmclient_dns_verified,
    post_verify_domain,
    pre_verify_domain,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .utils import is_taskable

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)

# a check every 5 minutes, for up to 4 hours.
VERIFY_DOMAIN_INTERVAL = 300
VERIFY_DOMAIN_MAX_ATTEMPTS = 48


class DomainCheck(str, Enum):
    """The result of one check of a domain."""

    VERIFIED = "verified"
    """The domain's DNS record exists, and the domain resolves."""

    MISSING = "missing"
    """The domain's DNS record does not exist, so checking again cannot help."""

    PENDING = "pending"
    """The DNS record exists, but the domain does not resolve yet.

    Check again later.
    """


def check_domain(
    domain_name: str, record_type: str = "A", hosted_zone_id: Optional[str] = None, task_id: Optional[str] = None
) -> DomainCheck:
    """
    Check once that a domain's DNS record exists, and that the domain resolves.

    It sends llmclient_dns_verified when the domain resolves, and llmclient_dns_failed when it does
    not resolve yet. It does not wait: the caller checks again later.

    :param domain_name: The domain name, which aws_helper.aws.domain_resolver() has resolved.
    :param record_type: The DNS record type, e.g. A.
    :param hosted_zone_id: The Route53 hosted zone of the record, by default that of the environment's api domain.
    :param task_id: The Celery task id, for logging and signals.
    """
    fn_name = f"{logger_prefix}.check_domain()"
    if not hosted_zone_id:
        customer_api_domain_hosted_zone = aws_helper.route53.get_hosted_zone(  # type: ignore[union-attr]
            smarter_settings.environment_api_domain
        )
        hosted_zone_id = aws_helper.route53.get_hosted_zone_id(  # type: ignore[union-attr]
            hosted_zone=customer_api_domain_hosted_zone
        )

    # 1. verify that the DNS record actually exists. If it doesn't then there's no point in checking again.
    dns_record = aws_helper.route53.get_dns_record(  # type: ignore[union-attr]
        hosted_zone_id=hosted_zone_id, record_name=domain_name, record_type=record_type
    )
    if not dns_record:
        logger.warning("%s DNS record for domain %s not found. task_id: %s", fn_name, domain_name, task_id)
        return DomainCheck.MISSING

    # 2. verify that the domain resolves
    try:
        dns_ns_records = {rdata.to_text() for rdata in dns.resolver.query(domain_name)}
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        logger.warning("%s unable to resolve domain %s task_id: %s", fn_name, domain_name, task_id)
        llmclient_dns_failed.send(
            sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
        )
        return DomainCheck.PENDING
    except dns.resolver.Timeout:
        logger.warning("%s timeout exceeded while querying the domain %s task_id: %s", fn_name, domain_name, task_id)
        llmclient_dns_failed.send(
            sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
        )
        return DomainCheck.PENDING

    logger.info(
        "%s successfully resolved domain %s using NS records %s task_id: %s",
        fn_name,
        domain_name,
        dns_ns_records,
        task_id,
    )
    llmclient_dns_verified.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
    return DomainCheck.VERIFIED


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.infrastructure_tasks_celery_task_queue,
)
def verify_domain(
    domain_name: str,
    record_type="A",
    llmclient_id: Optional[int] = None,
    activate_llmclient: bool = False,
    hosted_zone_id: Optional[str] = None,
    task_id: Optional[str] = None,
    attempt: int = 0,
) -> Optional[bool]:
    """
    Verify that an Internet domain name resolves to NS records.

    This Celery task checks that a domain name resolves to the expected DNS records (NS or other),
    sending verification signals and updating llmclient deployment status as appropriate. If the domain
    does not resolve yet, it schedules itself to check again in VERIFY_DOMAIN_INTERVAL seconds, up to
    VERIFY_DOMAIN_MAX_ATTEMPTS times, rather than sleeping.

    Parameters
    ----------
    domain_name : str
        The domain name to verify.
    record_type : str, optional
        The DNS record type to verify (default is "A").
    llmclient_id : int, optional
        The id of the LLMClient associated with the domain, if any.
    activate_llmclient : bool, optional
        Whether to activate the llmclient upon successful verification. Default is False.
    hosted_zone_id : str, optional
        The AWS Route53 hosted zone ID to use for DNS lookups.
    task_id : str, optional
        The Celery task ID for logging and signal purposes.
    attempt : int, optional
        The number of checks already made. The task passes it when it schedules itself again.

    Returns
    -------
    bool or None
        True if the domain is verified, False if it cannot be, and None if it will be checked again.

    Signals
    -------
    pre_verify_domain : django.dispatch.Signal
        Sent before domain verification begins.
    post_verify_domain : django.dispatch.Signal
        Sent after domain verification is completed.
    llmclient_dns_verification_initiated : django.dispatch.Signal
        Sent when DNS verification is initiated.
    llmclient_dns_failed : django.dispatch.Signal
        Sent when DNS verification fails.
    llmclient_dns_verified : django.dispatch.Signal
        Sent when DNS verification succeeds.

    Raises
    ------
    Exception
        Any exception raised during the verification process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return False
    if not aws_helper.route53:
        return False
    fn_name = f"{logger_prefix}.verify_domain()"
    task_id = task_id or verify_domain.request.id
    llmclient = LLMClient.objects.filter(pk=llmclient_id).first() if llmclient_id else None
    if attempt == 0:
        logger.info("%s - verifying domain %s task_id: %s", fn_name, domain_name, task_id)
        pre_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
        llmclient_dns_verification_initiated.send(
            sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
        )
    logger.info(
        "%s - Attempt %s of %s to verify domain %s task_id: %s",
        fn_name,
        attempt + 1,
        VERIFY_DOMAIN_MAX_ATTEMPTS,
        domain_name,
        task_id,
    )

    resolved_domain_name = aws_helper.aws.domain_resolver(domain_name)
    result = check_domain(resolved_domain_name, record_type=record_type, hosted_zone_id=hosted_zone_id, task_id=task_id)

    if result == DomainCheck.PENDING and attempt + 1 < VERIFY_DOMAIN_MAX_ATTEMPTS:
        # check again later, without blocking this worker while the DNS record propagates.
        verify_domain.apply_async(
            kwargs={
                "domain_name": domain_name,
                "record_type": record_type,
                "llmclient_id": llmclient_id,
                "activate_llmclient": activate_llmclient,
                "hosted_zone_id": hosted_zone_id,
                "task_id": task_id,
                "attempt": attempt + 1,
            },
            countdown=VERIFY_DOMAIN_INTERVAL,
        )
        return None

    if result != DomainCheck.VERIFIED:
        logger.error(
            "%s unable to verify domain %s after %s attempts task_id: %s", fn_name, domain_name, attempt + 1, task_id
        )
        if llmclient:
            llmclient_dns_failed.send(
                sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
            )
            llmclient.dns_verification_status = LLMClient.DnsVerificationStatusChoices.FAILED
            llmclient.save(asynchronous=True)
        post_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
        return False

    # if this domain is associated with a LLMClient then we should ensure that it is activated
    if activate_llmclient and llmclient and not llmclient.deployed:
        llmclient.deployed = True
        llmclient.save(asynchronous=True)
        logger.info(
            "%s LLMClient %s has been deployed to %s task_id: %s", fn_name, llmclient.name, domain_name, task_id
        )

    post_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
    return True
