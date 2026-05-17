"""
Celery tasks for verifying chatbot domain DNS records.

This module defines Celery tasks for verifying that Internet domain names resolve to the expected DNS records (NS or other),
including signal handling, chatbot deployment status updates, and retry logic.

Main Tasks
----------

- verify_domain(domain_name, record_type="A", chatbot=None, activate_chatbot=False, hosted_zone_id=None, task_id=None):
    Attempts to verify that a domain name resolves to the expected DNS records, updating chatbot deployment status and sending verification signals.

Signals
-------

- pre_verify_domain: Sent before domain verification begins.
- post_verify_domain: Sent after domain verification is completed.
- chatbot_dns_verification_initiated: Sent when DNS verification is initiated.
- chatbot_dns_failed: Sent when DNS verification fails.
- chatbot_dns_verified: Sent when DNS verification succeeds.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution, verification attempts, and results are logged using the smarter logging library, with waffle switches for task and chatbot logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously verify a chatbot domain:

    verify_domain.delay(domain_name, record_type, chatbot, activate_chatbot, hosted_zone_id, task_id)

Raises
------

Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

import time
from typing import Optional

import dns.resolver

from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.signals import (
    chatbot_dns_failed,
    chatbot_dns_verification_initiated,
    chatbot_dns_verified,
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
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.CHATBOT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def verify_domain(
    domain_name: str,
    record_type="A",
    chatbot: Optional[ChatBot] = None,
    activate_chatbot: bool = False,
    hosted_zone_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> bool:
    """
    Verify that an Internet domain name resolves to NS records.

    This Celery task attempts to verify that a domain name resolves to the expected DNS records (NS or other),
    sending verification signals and updating chatbot deployment status as appropriate. It retries verification
    multiple times, logging each attempt and result.

    Parameters
    ----------
    domain_name : str
        The domain name to verify.
    record_type : str, optional
        The DNS record type to verify (default is "A").
    chatbot : ChatBot, optional
        The ChatBot instance associated with the domain, if any.
    activate_chatbot : bool, optional
        Whether to activate the chatbot upon successful verification. Default is False.
    hosted_zone_id : str, optional
        The AWS Route53 hosted zone ID to use for DNS lookups.
    task_id : str, optional
        The Celery task ID for logging and signal purposes.

    Returns
    -------
    bool
        True if the domain is successfully verified, False otherwise.

    Signals
    -------
    pre_verify_domain : django.dispatch.Signal
        Sent before domain verification begins.
    post_verify_domain : django.dispatch.Signal
        Sent after domain verification is completed.
    chatbot_dns_verification_initiated : django.dispatch.Signal
        Sent when DNS verification is initiated.
    chatbot_dns_failed : django.dispatch.Signal
        Sent when DNS verification fails.
    chatbot_dns_verified : django.dispatch.Signal
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
    task_id = verify_domain.request.id or task_id
    logger.info("%s - verifying domain %s task_id: %s", fn_name, domain_name, task_id)

    pre_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
    chatbot_dns_verification_initiated.send(
        sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
    )

    domain_name = aws_helper.aws.domain_resolver(domain_name)
    sleep_interval = 300
    max_attempts = 48

    for i in range(max_attempts):
        logger.info(
            "%s - Attempt %s of %s to verify domain %s task_id: %s",
            fn_name,
            i + 1,
            max_attempts,
            domain_name,
            task_id,
        )
        if i > 0:
            time.sleep(sleep_interval)
            logger.warning(
                "%s Retrying verification of %s. Attempt: %s task_id: %s",
                fn_name,
                domain_name,
                i + 1,
                task_id,
            )

        # Check NS and SOA records
        try:
            # 1. verify that the DNS record actually exists. If it doesn't then there's no point in proceeding.
            if not hosted_zone_id:
                customer_api_domain_hosted_zone = aws_helper.route53.get_hosted_zone(
                    smarter_settings.environment_api_domain
                )
                hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=customer_api_domain_hosted_zone)

            dns_record = aws_helper.route53.get_dns_record(
                hosted_zone_id=hosted_zone_id, record_name=domain_name, record_type=record_type
            )
            if not dns_record:
                logger.warning(
                    "%s DNS record for domain %s not found. Nothing more to do, bailing out. task_id: %s",
                    fn_name,
                    domain_name,
                    task_id,
                )
                if chatbot:
                    chatbot_dns_failed.send(
                        sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
                    )
                    chatbot.dns_verification_status = ChatBot.DnsVerificationStatusChoices.FAILED
                    chatbot.save(asynchronous=True)
                post_verify_domain.send(
                    sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
                )
                return False

            # 2. verify that the domain resolves to the correct NS records
            dns_ns_records = {rdata.to_text() for rdata in dns.resolver.query(domain_name)}
            logger.info(
                "%s successfully resolved domain %s using NS records %s task_id: %s",
                fn_name,
                domain_name,
                dns_ns_records,
                task_id,
            )
            chatbot_dns_verified.send(
                sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
            )

            if not activate_chatbot:
                post_verify_domain.send(
                    sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
                )
                return True

            # 3. if this domain is associated with a ChatBot then we should ensure that it is activated
            if chatbot and not chatbot.deployed:
                chatbot.deployed = True
                chatbot.save(asynchronous=True)
                logger.info(
                    "%s Chatbot %s has been deployed to %s task_id: %s", fn_name, chatbot.name, domain_name, task_id
                )

            post_verify_domain.send(
                sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
            )
            return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            logger.warning("%s unable to resolve domain %s task_id: %s", fn_name, domain_name, task_id)
            chatbot_dns_failed.send(
                sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
            )
            continue
        except dns.resolver.Timeout:
            logger.warning(
                "%s timeout exceeded while querying the domain %s task_id: %s", fn_name, domain_name, task_id
            )
            chatbot_dns_failed.send(
                sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
            )
            continue

    logger.error(
        "%s unable to verify domain %s after %s attempts task_id: %s", fn_name, domain_name, max_attempts, task_id
    )
    post_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
    chatbot_dns_failed.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
    return False
