"""
Celery tasks for verifying llmclient custom domains.

This module defines Celery tasks for verifying the NS records of AWS Route53 hosted zones for llmclient custom domains, including periodic re-verification, signal handling, and notification of account owners.

Main Tasks
----------

- verify_custom_domain(hosted_zone_id, sleep_interval=None, max_attempts=None):
    Periodically verifies the NS records of a hosted zone to ensure they match DNS records, updating verification status and notifying the account owner.

Signals
-------

- pre_verify_custom_domain: Sent before custom domain verification begins.
- post_verify_custom_domain: Sent after custom domain verification is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution, verification attempts, and results are logged using the smarter logging library, with waffle switches for task and llmclient logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously verify an llmclient custom domain:

    verify_custom_domain.delay(hosted_zone_id, sleep_interval, max_attempts)

Raises
------

LLMClientTaskError
    If the hosted zone data is not in the expected format.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from typing import Optional

import dns.resolver

from smarter.apps.account.models import Account, AccountContact
from smarter.apps.llmclient.models import LLMClient, LLMClientCustomDomain
from smarter.apps.llmclient.signals import (
    post_verify_custom_domain,
    pre_verify_custom_domain,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CUSTOMER_SUPPORT_EMAIL
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .exceptions import LLMClientTaskError
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
def verify_custom_domain(
    hosted_zone_id: str,
    sleep_interval: Optional[int] = None,
    max_attempts: Optional[int] = None,
    attempt: int = 0,
    task_id: Optional[str] = None,
) -> Optional[bool]:
    """
    Verify the NS records of an AWS Route53 hosted zone for a custom domain.

    This Celery task periodically checks the NS records of a hosted zone to ensure they match DNS records,
    marking the custom domain as verified or not verified, and notifying the account owner of the result.
    Pre- and post-verification signals are sent, and all actions are logged.

    A domain's name servers can take a day to change. Each run checks once, and if the domain is not
    verified yet, the task schedules itself to check again in sleep_interval seconds, up to max_attempts
    times, rather than sleeping, so that it never blocks a Celery worker while it waits.

    Parameters
    ----------
    hosted_zone_id : str
        The ID of the AWS Route53 hosted zone to verify.
    sleep_interval : int, optional
        The interval in seconds to wait between verification attempts. Default is 1800 (30 minutes).
    max_attempts : int, optional
        The maximum number of verification attempts. Default is calculated for 24 hours.
    attempt : int, optional
        The number of checks already made. The task passes it when it schedules itself again.
    task_id : str, optional
        The id of the first run, for logging and signals.

    Returns
    -------
    bool or None
        True if the hosted zone is verified, False if it is not after max_attempts checks, and None
        if it will be checked again.

    Signals
    -------
    pre_verify_custom_domain : django.dispatch.Signal
        Sent before custom domain verification begins.
    post_verify_custom_domain : django.dispatch.Signal
        Sent after custom domain verification is completed.

    Raises
    ------
    LLMClientTaskError
        If the hosted zone data is not in the expected format.
    Exception
        Any exception raised during the verification process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return False
    if not aws_helper.route53:
        return False

    fn_name = logger_prefix + ".verify_custom_domain()"
    task_id = task_id or verify_custom_domain.request.id
    HOURS = 24
    sleep_interval = sleep_interval or 1800
    max_attempts = max_attempts or int(HOURS * (3600 / sleep_interval))

    if attempt == 0:
        logger.info("%s - verifying AWS Route53 Hosted Zone %s task_id: %s", fn_name, hosted_zone_id, task_id)
        pre_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)

    hosted_zone = aws_helper.route53.get_hosted_zone_by_id(hosted_zone_id=hosted_zone_id)
    if not isinstance(hosted_zone, dict):
        raise LLMClientTaskError(f"expected a dict but received {type(hosted_zone)}")
    domain_name = hosted_zone["HostedZone"]["Name"]
    logger.info(
        "%s - %s %s Attempt: %s of %s task_id: %s",
        fn_name,
        hosted_zone_id,
        domain_name,
        attempt + 1,
        max_attempts,
        task_id,
    )

    if _ns_records_verified(hosted_zone_id, domain_name, task_id):
        logger.info(
            "%s AWS Route53 Hosted Zone %s %s verified. task_id %s", fn_name, hosted_zone_id, domain_name, task_id
        )
        # if this is a customer custom domain, we should update the database to reflect that
        # the domain is verified.
        LLMClientCustomDomain.objects.filter(aws_hosted_zone_id=hosted_zone_id).update(is_verified=True)

        # send an email to the account owner to notify them that the domain has been verified
        account = _account_for(hosted_zone_id)
        if account:
            subject = f"Domain Verification for {domain_name} Successful"
            body = f"""Your domain {domain_name} has been verified.\n\n
            Your custom domain is now active and ready to use with your LLMClient.
            If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."""
            AccountContact.send_email_to_account(account=account, subject=subject, body=body)
            logger.info(
                "%s - Domain %s has been verified for account %s %s task_id: %s",
                fn_name,
                domain_name,
                account.company_name,
                account.account_number,
                task_id,
            )
        else:
            logger.info("%s domain %s is not a LLMClient custom domain.", fn_name, domain_name)
        post_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)
        return True

    # the hosted zone is not verified, so update the custom domain record to reflect that.
    LLMClientCustomDomain.objects.filter(aws_hosted_zone_id=hosted_zone_id, is_verified=True).update(is_verified=False)

    if attempt + 1 < max_attempts:
        # check again later, without blocking this worker while the name servers change.
        verify_custom_domain.apply_async(
            kwargs={
                "hosted_zone_id": hosted_zone_id,
                "sleep_interval": sleep_interval,
                "max_attempts": max_attempts,
                "attempt": attempt + 1,
                "task_id": task_id,
            },
            countdown=sleep_interval,
        )
        return None

    # send an email to the account owner to notify them that the domain verification failed
    account = _account_for(hosted_zone_id)
    if account:
        subject = f"Domain Verification Failure for {domain_name}"
        body = f"""We were unable to verify your domain {domain_name}.\n\n
        We made {max_attempts} attempts over a period of {HOURS} hours to verify the domain.
        If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."""
        AccountContact.send_email_to_account(account=account, subject=subject, body=body)
        logger.error(
            "%s - Domain verification failed for domain %s for account %s %s task_id: %s",
            fn_name,
            domain_name,
            account.company_name,
            account.account_number,
            task_id,
        )
    else:
        logger.error("%s - Domain verification failed for domain %s task_id: %s", fn_name, domain_name, task_id)
    post_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)
    return False


def _ns_records_verified(hosted_zone_id: str, domain_name: str, task_id: Optional[str]) -> bool:
    """Check once whether the domain's public NS records include one of its Route53 hosted zone's name servers."""
    fn_name = logger_prefix + "._ns_records_verified()"
    try:
        dns_ns_records = {rdata.to_text() for rdata in dns.resolver.query(domain_name, "NS")}
    except dns.resolver.NXDOMAIN:
        logger.warning("%s domain %s does not exist.", fn_name, domain_name)
        return False
    except dns.resolver.Timeout:
        logger.warning("%s timeout exceeded while querying the domain %s.", fn_name, domain_name)
        return False
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("%s unexpected error while querying domain %s: %s", fn_name, domain_name, str(e))
        return False

    aws_ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=hosted_zone_id)  # type: ignore[union-attr]
    for i, record in enumerate(aws_ns_records, start=1):
        logger.info(
            "%s checking AWS NS record %s (%s of %s) against DNS NS records %s task_id: %s",
            fn_name,
            record["Value"],
            i,
            len(aws_ns_records),
            dns_ns_records,
            task_id,
        )
        if record["Value"] in dns_ns_records:
            return True
    return False


def _account_for(hosted_zone_id: str) -> Optional[Account]:
    """
    Return the account of the LLMClient that uses the custom domain of a hosted zone, if any.

    LLMClientCustomDomain has no owner of its own: it belongs to the LLMClient whose
    custom_domain it is.
    """
    llmclient = LLMClient.objects.filter(custom_domain__aws_hosted_zone_id=hosted_zone_id).first()
    return llmclient.user_profile.account if llmclient else None
