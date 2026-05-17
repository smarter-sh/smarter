"""
Celery tasks for undeploying chatbot default API domains.

This module defines Celery tasks for reversing chatbot deployments by destroying the customer API default domain A record and updating deployment status.

Main Tasks
----------

- undeploy_default_api(chatbot_id):
    Reverses a chatbot deployment by destroying the customer API default domain A record and updating the chatbot's deployment state.

Signals
-------

- pre_undeploy_default_api: Sent before undeployment of the default API begins.
- post_undeploy_default_api: Sent after undeployment of the default API is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and undeployment actions are logged using the smarter logging library, with waffle switches for task and chatbot logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously undeploy a chatbot default API domain:

    undeploy_default_api.delay(chatbot_id)

Raises
------

ChatBot.DoesNotExist
    If the ChatBot with the given ID does not exist.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.signals import (
    post_undeploy_default_api,
    pre_undeploy_default_api,
)
from smarter.common.conf import smarter_settings
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
def undeploy_default_api(chatbot_id: int):
    """
    Reverse a Chatbot deployment by destroying the customer API default domain A record for a chatbot.

    This Celery task performs the following steps:
    1. Sends a pre-undeploy signal for the chatbot API.
    2. Logs the undeployment request.
    3. Retrieves the ChatBot instance by ID.
    4. Marks the chatbot as not deployed and resets DNS verification status.
    5. Saves the chatbot state and sends a post-undeploy signal.

    Parameters
    ----------
    chatbot_id : int
        The primary key of the ChatBot instance to be undeployed.

    Signals
    -------
    pre_undeploy_default_api : django.dispatch.Signal
        Sent before undeployment of the default API begins.
    post_undeploy_default_api : django.dispatch.Signal
        Sent after undeployment of the default API is completed.

    Raises
    ------
    ChatBot.DoesNotExist
        If the ChatBot with the given ID does not exist.
    Exception
        Any exception raised during the undeployment process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return

    task_id = undeploy_default_api.request.id
    prefix = logger_prefix + f".{undeploy_default_api.__name__}()"
    logger.info("%s - chatbot %s task_id: %s", prefix, chatbot_id, task_id)
    pre_undeploy_default_api.send(sender=undeploy_default_api, chatbot_id=chatbot_id, task_id=task_id)

    chatbot: ChatBot
    try:
        chatbot = ChatBot.objects.get(id=chatbot_id)
    except ChatBot.DoesNotExist:
        logger.error("%s Chatbot %s not found. task_id: %s", prefix, chatbot_id, task_id)
        post_undeploy_default_api.send(sender=undeploy_default_api, chatbot_id=chatbot_id)
        return None

    chatbot.deployed = False
    chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.NOT_VERIFIED
    chatbot.save(asynchronous=True)
    post_undeploy_default_api.send(sender=undeploy_default_api, chatbot_id=chatbot_id, task_id=task_id)
