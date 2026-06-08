"""
Celery tasks for undeploying llm_client default API domains.

This module defines Celery tasks for reversing llm_client deployments by destroying the customer API default domain A record and updating deployment status.

Main Tasks
----------

- undeploy_default_api(llm_client_id):
    Reverses a llm_client deployment by destroying the customer API default domain A record and updating the llm_client's deployment state.

Signals
-------

- pre_undeploy_default_api: Sent before undeployment of the default API begins.
- post_undeploy_default_api: Sent after undeployment of the default API is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and undeployment actions are logged using the smarter logging library, with waffle switches for task and llm_client logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously undeploy a llm_client default API domain:

    undeploy_default_api.delay(llm_client_id)

Raises
------

LLMClient.DoesNotExist
    If the LLMClient with the given ID does not exist.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from smarter.apps.llm_client.models import LLMClient
from smarter.apps.llm_client.signals import (
    post_undeploy_default_api,
    pre_undeploy_default_api,
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
    retry_backoff=smarter_settings.llm_client_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llm_client_tasks_celery_max_retries,
    queue=smarter_settings.llm_client_tasks_celery_task_queue,
)
def undeploy_default_api(llm_client_id: int):
    """
    Reverse a LLMClient deployment by destroying the customer API default domain A record for a llm_client.

    This Celery task performs the following steps:
    1. Sends a pre-undeploy signal for the llm_client API.
    2. Logs the undeployment request.
    3. Retrieves the LLMClient instance by ID.
    4. Marks the llm_client as not deployed and resets DNS verification status.
    5. Saves the llm_client state and sends a post-undeploy signal.

    Parameters
    ----------
    llm_client_id : int
        The primary key of the LLMClient instance to be undeployed.

    Signals
    -------
    pre_undeploy_default_api : django.dispatch.Signal
        Sent before undeployment of the default API begins.
    post_undeploy_default_api : django.dispatch.Signal
        Sent after undeployment of the default API is completed.

    Raises
    ------
    LLMClient.DoesNotExist
        If the LLMClient with the given ID does not exist.
    Exception
        Any exception raised during the undeployment process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return

    task_id = undeploy_default_api.request.id
    prefix = logger_prefix + f".{undeploy_default_api.__name__}()"
    logger.info("%s - llm_client %s task_id: %s", prefix, llm_client_id, task_id)
    pre_undeploy_default_api.send(sender=undeploy_default_api, llm_client_id=llm_client_id, task_id=task_id)

    llm_client: LLMClient
    try:
        llm_client = LLMClient.objects.get(id=llm_client_id)
    except LLMClient.DoesNotExist:
        logger.error("%s LLMClient %s not found. task_id: %s", prefix, llm_client_id, task_id)
        post_undeploy_default_api.send(sender=undeploy_default_api, llm_client_id=llm_client_id)
        return None

    llm_client.deployed = False
    llm_client.dns_verification_status = llm_client.DnsVerificationStatusChoices.NOT_VERIFIED
    llm_client.save(asynchronous=True)
    post_undeploy_default_api.send(sender=undeploy_default_api, llm_client_id=llm_client_id, task_id=task_id)
