"""
Celery tasks for the llmclient app.

This module defines Celery tasks related to llmclient request handling, including the creation of llmclient request records.

Main Tasks
----------

- create_llmclient_request(llmclient_id, request_data):
    Creates a LLMClientRequests record for a given llmclient and request data. Handles pre- and post-create signals, logging, and error retries.

Signals
-------

- pre_create_llmclient_request: Sent before a LLMClientRequests record is created.
- post_create_llmclient_request: Sent after a LLMClientRequests record is created.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and request data are logged using the smarter logging library, with waffle switches for task and llmclient logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously create llmclient request records:

    create_llmclient_request.delay(llmclient_id, request_data)

Raises
------

LLMClient.DoesNotExist
    If the LLMClient with the given ID does not exist.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from smarter.apps.llmclient.models import LLMClient, LLMClientRequests
from smarter.apps.llmclient.signals import (
    post_create_llmclient_request,
    pre_create_llmclient_request,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.llmclient_tasks_celery_task_queue,
)
def create_llmclient_request(llmclient_id: int, request_data: dict):
    """
    Create a LLMClient request record in the database as a Celery task.

    This task performs the following steps:
    1. Sends a pre-create signal for the llmclient request.
    2. Logs the incoming request data.
    3. Retrieves the LLMClient instance by ID.
    4. Extracts the session key from the request data.
    5. Creates a LLMClientRequests record with the llmclient, request data, and session key.
    6. Sends a post-create signal for the llmclient request.

    Parameters
    ----------
    llmclient_id : int
        The primary key of the LLMClient instance for which the request is being created.
    request_data : dict
        The data associated with the llmclient request. Should include all relevant request fields.

    Signals
    -------
    pre_create_llmclient_request : django.dispatch.Signal
        Sent before the LLMClientRequests record is created.
    post_create_llmclient_request : django.dispatch.Signal
        Sent after the LLMClientRequests record is created.

    Raises
    ------
    LLMClient.DoesNotExist
        If the LLMClient with the given ID does not exist.
    Exception
        Any exception raised during the creation process will trigger a retry according to Celery settings.
    """

    task_id = create_llmclient_request.request.id
    pre_create_llmclient_request.send(
        sender=create_llmclient_request, llmclient_id=llmclient_id, request_data=request_data, task_id=task_id
    )
    logger.info(
        "%s - llmclient %s task_id: %s received request data: %s",
        logger_prefix + f".{create_llmclient_request.__name__}() task_id: %s",
        llmclient_id,
        task_id,
        request_data,
    )
    llmclient = LLMClient.objects.get(id=llmclient_id)
    session_key = request_data.get(SMARTER_CHAT_SESSION_KEY_NAME)
    LLMClientRequests.objects.create(llmclient=llmclient, request=request_data, session_key=session_key)
    post_create_llmclient_request.send(
        sender=create_llmclient_request, llmclient_id=llmclient_id, request_data=request_data, task_id=task_id
    )
