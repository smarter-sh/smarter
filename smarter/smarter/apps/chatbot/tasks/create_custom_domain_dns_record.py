"""
Celery tasks for chatbot custom domain DNS record management.

This module defines Celery tasks for creating and managing DNS records for chatbot custom domains using AWS Route53.

Main Tasks
----------

- create_custom_domain_dns_record(chatbot_custom_domain_id, record_name, record_type, record_value, record_ttl=600):
    Gets or creates a DNS record in an AWS Route53 hosted zone for a chatbot custom domain. Handles pre- and post-create signals, logging, and error retries.

Signals
-------

- pre_create_custom_domain_dns_record: Sent before a DNS record is created in the database.
- post_create_custom_domain_dns_record: Sent after a DNS record is created in the database.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and DNS record creation are logged using the smarter logging library, with waffle switches for task and chatbot logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously create or update DNS records for chatbot custom domains:

    create_custom_domain_dns_record.delay(chatbot_custom_domain_id, record_name, record_type, record_value, record_ttl)

Raises
------

ChatBotCustomDomainNotFound
    If the ChatBotCustomDomain with the given ID does not exist.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from smarter.apps.chatbot.models import (
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
)
from smarter.apps.chatbot.signals import (
    post_create_custom_domain_dns_record,
    pre_create_custom_domain_dns_record,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws.route53 import AWSRoute53
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .exceptions import ChatBotCustomDomainNotFound
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
def create_custom_domain_dns_record(
    chatbot_custom_domain_id: int, record_name: str, record_type: str, record_value: str, record_ttl: int = 600
):
    """
    Get or create a DNS record in an AWS Route53 hosted zone for a chatbot custom domain.

    This Celery task performs the following steps:
    1. Sends a pre-create signal for the DNS record.
    2. Logs the DNS record creation request.
    3. Retrieves the ChatBotCustomDomain instance by ID.
    4. Uses AWSRoute53 helper to get or create the DNS record in the specified hosted zone.
    5. Updates or creates the ChatBotCustomDomainDNS record in the database.
    6. Sends a post-create signal for the DNS record.

    Parameters
    ----------
    chatbot_custom_domain_id : int
        The primary key of the ChatBotCustomDomain instance.
    record_name : str
        The DNS record name (e.g., 'example.com.').
    record_type : str
        The DNS record type (e.g., 'A', 'CNAME').
    record_value : str
        The value for the DNS record (e.g., IP address or CNAME target).
    record_ttl : int, optional
        The TTL (time to live) for the DNS record, in seconds. Default is 600.

    Returns
    -------
    dict
        The DNS record details as returned by AWS Route53, for example:

        {
            'Name': 'example.com.',
            'Type': 'A',
            'TTL': 300,
            'ResourceRecords': [
                {'Value': '192.0.2.44'},
            ],
        }

    Signals
    -------
    pre_create_custom_domain_dns_record : django.dispatch.Signal
        Sent before the DNS record is created in the database.
    post_create_custom_domain_dns_record : django.dispatch.Signal
        Sent after the DNS record is created in the database.

    Raises
    ------
    ChatBotCustomDomainNotFound
        If the ChatBotCustomDomain with the given ID does not exist.
    Exception
        Any exception raised during the creation process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return
    if not isinstance(aws_helper.route53, AWSRoute53):
        return

    task_id = create_custom_domain_dns_record.request.id

    logger.info(
        "%s - creating DNS record %s %s for ChatBotCustomDomain %s task_id: %s",
        logger_prefix + ".create_custom_domain_dns_record() task_id: %s",
        record_type,
        record_name,
        chatbot_custom_domain_id,
        task_id,
    )

    pre_create_custom_domain_dns_record.send(
        sender=create_custom_domain_dns_record,
        chatbot_custom_domain_id=chatbot_custom_domain_id,
        record_name=record_name,
        record_type=record_type,
        record_value=record_value,
        record_ttl=record_ttl,
        task_id=task_id,
    )
    try:
        custom_domain = ChatBotCustomDomain.objects.get(id=chatbot_custom_domain_id)
    except ChatBotCustomDomain.DoesNotExist as e:
        err = f"{logger_prefix}.create_custom_domain_dns_record() - ChatBotCustomDomain {chatbot_custom_domain_id} not found. task_id: {task_id}"
        logger.error(err)
        raise ChatBotCustomDomainNotFound(err) from e

    record, _ = aws_helper.route53.get_or_create_dns_record(
        hosted_zone_id=custom_domain.aws_hosted_zone_id,
        record_name=record_name,
        record_type=record_type,
        record_value=record_value,  # type: ignore
        record_ttl=record_ttl,
    )
    try:
        # note: we cannot use the get_or_create method here because
        # of validation errors that are raised if record_value is
        # not present.
        dns_record = ChatBotCustomDomainDNS.objects.get(
            custom_domain=custom_domain,
            record_name=record["Name"],
            record_type=record["Type"],
        )
        dns_record.record_value = (record["ResourceRecords"],)
        dns_record.record_ttl = (record["TTL"],)
        dns_record.save()
    except ChatBotCustomDomainDNS.DoesNotExist:
        dns_record = ChatBotCustomDomainDNS(
            custom_domain=custom_domain,
            record_name=record["Name"],
            record_type=record["Type"],
            record_value=record["ResourceRecords"],
            record_ttl=record["TTL"],
        )

    post_create_custom_domain_dns_record.send(
        sender=create_custom_domain_dns_record,
        chatbot_custom_domain_id=chatbot_custom_domain_id,
        record_name=record_name,
        record_type=record_type,
        record_value=record_value,
        record_ttl=record_ttl,
        task_id=task_id,
    )
