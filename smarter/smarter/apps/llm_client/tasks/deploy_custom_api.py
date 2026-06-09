"""
Celery tasks for deploying llm_client custom API domains.

This module defines Celery tasks for deploying custom API domains for llm_clients, including the creation and verification of Route53 A records for customer APIs.

Main Tasks
----------

- deploy_custom_api(llm_client_id):
    Creates a custom domain A record for an llm_client's customer API and verifies the hosted zone.

Signals
-------

- pre_deploy_custom_api: Sent before deployment of the custom API begins.
- post_deploy_custom_api: Sent after deployment of the custom API is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and domain deployment are logged using the smarter logging library, with waffle switches for task and llm_client logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously deploy an llm_client custom API domain:

    deploy_custom_api.delay(llm_client_id)

Raises
------

LLMClient.DoesNotExist
    If the LLMClient with the given ID does not exist.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from smarter.apps.llm_client.models import LLMClient
from smarter.apps.llm_client.signals import (
    post_deploy_custom_api,
    pre_deploy_custom_api,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .utils import is_taskable
from .verify_custom_domain import verify_custom_domain

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
def deploy_custom_api(llm_client_id: int):
    """
    Create a custom domain A record for an llm_client's customer API.

    This Celery task performs the following steps:
    1. Sends a pre-deploy signal for the llm_client API.
    2. Logs the deployment request.
    3. Retrieves the LLMClient instance by ID.
    4. Checks for a valid custom domain; logs and exits if missing or not validated.
    5. Creates a Route53 A record for the llm_client's custom domain.
    6. Verifies the hosted zone of the custom domain.
    7. Sends a post-deploy signal for the llm_client API.

    Parameters
    ----------
    llm_client_id : int
        The primary key of the LLMClient instance for which the custom domain A record is being created.

    Signals
    -------
    pre_deploy_custom_api : django.dispatch.Signal
        Sent before the deployment of the custom API begins.
    post_deploy_custom_api : django.dispatch.Signal
        Sent after the deployment of the custom API is completed.

    Raises
    ------
    LLMClient.DoesNotExist
        If the LLMClient with the given ID does not exist.
    Exception
        Any exception raised during the deployment process will trigger a retry according to Celery settings.
    """
    pre_deploy_custom_api.send(sender=deploy_custom_api, llm_client_id=llm_client_id)
    prefix = logger_prefix + f".{deploy_custom_api.__name__}()"
    task_id = deploy_custom_api.request.id
    logger.info("%s - llm_client %s task_id: %s", prefix, llm_client_id, task_id)

    llm_client = LLMClient.objects.get(id=llm_client_id)
    domain_name = llm_client.custom_domain

    if not domain_name:
        logger.warning(
            "%s Custom domain is missing or is not yet validated for %s llm_client %s task_id: %s. Nothing to do, returning.",
            prefix,
            llm_client.user_profile.account.company_name,
            llm_client.name,
            task_id,
        )
        post_deploy_custom_api.send(sender=deploy_custom_api, llm_client_id=llm_client_id, task_id=task_id)
        return

    if not is_taskable():
        return

    aws_helper.route53.create_domain_a_record(hostname=domain_name, api_host_domain=domain_name)  # type: ignore[union-attr]

    # verify the hosted zone of the custom domain
    hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name)  # type: ignore[union-attr]
    verify_custom_domain(hosted_zone_id)
    post_deploy_custom_api.send(sender=deploy_custom_api, llm_client_id=llm_client_id, task_id=task_id)
