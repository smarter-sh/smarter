"""
Celery tasks for verifying llm_client custom domains.

This module defines Celery tasks for verifying the NS records of AWS Route53 hosted zones for llm_client custom domains, including periodic re-verification, signal handling, and notification of account owners.

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

Task execution, verification attempts, and results are logged using the smarter logging library, with waffle switches for task and llm_client logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously verify a llm_client custom domain:

    verify_custom_domain.delay(hosted_zone_id, sleep_interval, max_attempts)

Raises
------

LLMClientTaskError
    If the hosted zone data is not in the expected format.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

import time
from typing import Optional

import dns.resolver

from smarter.apps.account.models import AccountContact
from smarter.apps.llm_client.models import LLMClientCustomDomain
from smarter.apps.llm_client.signals import (
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
    retry_backoff=smarter_settings.llm_client_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llm_client_tasks_celery_max_retries,
    queue=smarter_settings.llm_client_tasks_celery_task_queue,
)
def verify_custom_domain(
    hosted_zone_id: str,
    sleep_interval: Optional[int] = None,
    max_attempts: Optional[int] = None,
) -> bool:
    """
    Verify the NS records of an AWS Route53 hosted zone for a custom domain.

    This Celery task periodically checks the NS records of a hosted zone to ensure they match DNS records,
    marking the custom domain as verified or not verified, and notifying the account owner of the result.
    Pre- and post-verification signals are sent, and all actions are logged.

    Parameters
    ----------
    hosted_zone_id : str
        The ID of the AWS Route53 hosted zone to verify.
    sleep_interval : int, optional
        The interval in seconds to wait between verification attempts. Default is 1800 (30 minutes).
    max_attempts : int, optional
        The maximum number of verification attempts. Default is calculated for 24 hours.

    Returns
    -------
    bool
        True if the hosted zone is verified, False otherwise.

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
    task_id = verify_custom_domain.request.id
    logger.info(
        "%s - verifying AWS Route53 Hosted Zone %s task_id: %s",
        fn_name,
        hosted_zone_id,
        task_id,
    )

    pre_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)

    HOURS = 24
    hosted_zone = aws_helper.route53.get_hosted_zone_by_id(hosted_zone_id=hosted_zone_id)
    if not isinstance(hosted_zone, dict):
        raise LLMClientTaskError(f"expected a dict but received {type(hosted_zone)}")
    domain_name = hosted_zone["HostedZone"]["Name"]
    aws_ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=hosted_zone_id)
    sleep_interval = sleep_interval or 1800
    max_attempts = max_attempts or int(HOURS * (3600 / sleep_interval))

    logger.info("%s - %s %s", fn_name, hosted_zone_id, domain_name)
    for i in range(max_attempts):  # 24 hours * attempts per hour * 2 days
        if i > 0:
            time.sleep(sleep_interval)  # Wait for 30 minutes before the next attempt
            logger.warning(
                "%s retrying verification of AWS Route53 Hosted Zone %s %s Attempt: %s of %s task_id: %s",
                fn_name,
                hosted_zone_id,
                domain_name,
                i + 1,
                max_attempts,
                task_id,
            )

        # Check NS and SOA records
        try:
            dns_ns_records = {rdata.to_text() for rdata in dns.resolver.query(domain_name, "NS")}
        except dns.resolver.NXDOMAIN:
            logger.warning("%s domain %s does not exist.", fn_name, domain_name)
            continue
        except dns.resolver.Timeout:
            logger.warning("%s timeout exceeded while querying the domain %s.", fn_name, domain_name)
            continue
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s unexpected error while querying domain %s: %s", fn_name, domain_name, str(e))
            continue

        j = 0
        for record in aws_ns_records:
            j += 1
            logger.info(
                "%s checking AWS NS record %s (%s of %s) against DNS NS records %s task_id: %s",
                fn_name,
                record["Value"],
                j,
                len(aws_ns_records),
                dns_ns_records,
                task_id,
            )
            aws_ns_value = record["Value"]
            if aws_ns_value in dns_ns_records:
                logger.info(
                    "%s AWS Route53 Hosted Zone %s %s verified. task_id %s",
                    fn_name,
                    hosted_zone_id,
                    domain_name,
                    task_id,
                )
                # if this is a customer custom domain, we should update the database to reflect that
                # the domain is verified.
                try:
                    custom_domain = LLMClientCustomDomain.objects.get(aws_hosted_zone_id=hosted_zone_id)
                    custom_domain.is_verified = True
                    custom_domain.save()
                except LLMClientCustomDomain.DoesNotExist:
                    logger.info("%s domain %s is not a LLMClient custom domain.", fn_name, domain_name)

                # send an email to the account owner to notify them that the domain has been verified
                subject = f"Domain Verification for {domain_name} Successful"
                body = f"""Your domain {domain_name} has been verified.\n\n
                Your custom domain is now active and ready to use with your LLMClient.
                If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."""
                try:
                    account = LLMClientCustomDomain.objects.get(aws_hosted_zone_id=hosted_zone_id).user_profile.account
                    AccountContact.send_email_to_account(account=account, subject=subject, body=body)
                    msg = f"{fn_name} - Domain {domain_name} has been verified for account {account.company_name} {account.account_number} task_id: {task_id}"
                    logger.info(msg)
                except LLMClientCustomDomain.DoesNotExist:
                    pass

                post_verify_custom_domain.send(
                    sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id
                )
                return True

        # If we get here, then the hosted zone is not verified
        # and we should update the custom domain record to reflect that.
        try:
            hosted_zone = LLMClientCustomDomain.objects.get(aws_hosted_zone_id=hosted_zone_id, is_verified=True)
            hosted_zone.is_verified = False
            hosted_zone.save()
        except LLMClientCustomDomain.DoesNotExist:
            continue

    # send an email to the account owner to notify them that the domain verification failed
    subject = f"Domain Verification Failure for {domain_name}"
    body = f"""We were unable to verify your domain {domain_name}.\n\n
    We made {max_attempts} attempts over a period of {HOURS} hours to verify the domain.
    If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."""
    account = LLMClientCustomDomain.objects.get(hosted_zone_id=hosted_zone_id).user_profile.account
    AccountContact.send_email_to_account(account=account, subject=subject, body=body)
    msg = f"{fn_name} - Domain verification failed for domain {domain_name} for account {account.company_name} {account.account_number} task_id: {task_id}"
    logger.error(msg)
    post_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)
    return False
