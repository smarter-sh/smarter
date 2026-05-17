"""
Celery tasks for destroying chatbot domain A records.

This module defines tasks for destroying A records in AWS Route53 for chatbot domains, including signal handling and logging.

Main Tasks
----------

- destroy_domain_A_record(hostname, api_host_domain):
    Destroys the A record for a given domain name in AWS Route53.

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

Import this module and call the function as needed to destroy a chatbot domain A record:

    destroy_domain_A_record(hostname, api_host_domain)

Raises
------

Exception
    Any exception during task execution will be logged and may be handled by the caller.
"""

from smarter.apps.chatbot.signals import (
    post_destroy_domain_A_record,
    pre_destroy_domain_A_record,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .utils import is_taskable

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.CHATBOT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


def destroy_domain_A_record(hostname: str, api_host_domain: str):
    """
    Destroy the A record for a given domain name in AWS Route53.

    This function locates the hosted zone for the specified parent domain, retrieves the A record for the given hostname,
    and deletes it from Route53. It sends pre- and post-destroy signals and logs all actions.

    Parameters
    ----------
    hostname : str
        The domain name whose A record should be destroyed.
    api_host_domain : str
        The parent domain used to locate the AWS Route53 hosted zone.

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
    if not aws_helper.route53:
        return

    task_id = destroy_domain_A_record.request.id
    pre_destroy_domain_A_record.send(
        sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain, task_id=task_id
    )

    fn_name = logger_prefix + ".destroy_domain_A_record()"
    hostname = aws_helper.aws.domain_resolver(hostname)
    api_host_domain = aws_helper.aws.domain_resolver(api_host_domain)
    logger.info("%s - %s task_id: %s", fn_name, hostname, task_id)

    # locate the aws route53 hosted zone for the customer API domain
    hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=api_host_domain)
    logger.info(
        "%s found hosted zone %s for parent domain %s task_id: %s", fn_name, hosted_zone_id, api_host_domain, task_id
    )

    # retrieve the A record from the environment domain hosted zone. we'll
    # use this to create the A record in the customer API domain. example:
    # {
    #     "Name": "example.com.",
    #     "Type": "A",
    #     "TTL": 300,
    #     "ResourceRecords": [{"Value": "192.1.1.1"}]
    # }

    a_record = aws_helper.route53.get_dns_record(
        hosted_zone_id=hosted_zone_id,
        record_name=hostname,
        record_type="A",
    )
    if not a_record:
        logger.error(
            "%s a record not found for %s. Nothing to do, returning. task_id: %s", fn_name, api_host_domain, task_id
        )
        post_destroy_domain_A_record.send(
            sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain
        )
        return

    logger.info("%s a_record: %s task_id: %s", fn_name, a_record, task_id)
    record_type = a_record.get("Type", "A")
    record_ttl = a_record.get("TTL", smarter_settings.chatbot_tasks_default_ttl)
    alias_target = a_record.get("AliasTarget")
    record_resource_records = a_record.get("ResourceRecords")
    aws_helper.route53.destroy_dns_record(
        hosted_zone_id=hosted_zone_id,
        record_name=hostname,
        record_type=record_type,
        record_ttl=record_ttl,
        alias_target=alias_target,
        record_resource_records=record_resource_records,
    )
    post_destroy_domain_A_record.send(
        sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain, task_id=task_id
    )
