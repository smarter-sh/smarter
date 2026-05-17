"""
Celery tasks for the chatbot app.

This module defines Celery tasks related to chatbot request handling, including the creation of chatbot request records.

Main Tasks
----------

- create_chatbot_request(chatbot_id, request_data):
    Creates a ChatBotRequests record for a given chatbot and request data. Handles pre- and post-create signals, logging, and error retries.

Signals
-------

- pre_create_chatbot_request: Sent before a ChatBotRequests record is created.
- post_create_chatbot_request: Sent after a ChatBotRequests record is created.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and request data are logged using the smarter logging library, with waffle switches for task and chatbot logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously create chatbot request records:

    create_chatbot_request.delay(chatbot_id, request_data)

Raises
------

ChatBot.DoesNotExist
    If the ChatBot with the given ID does not exist.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from smarter.apps.chatbot.models import ChatBot, ChatBotRequests
from smarter.apps.chatbot.signals import (
    post_create_chatbot_request,
    pre_create_chatbot_request,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

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
def create_chatbot_request(chatbot_id: int, request_data: dict):
    """
    Create a ChatBot request record in the database as a Celery task.

    This task performs the following steps:
    1. Sends a pre-create signal for the chatbot request.
    2. Logs the incoming request data.
    3. Retrieves the ChatBot instance by ID.
    4. Extracts the session key from the request data.
    5. Creates a ChatBotRequests record with the chatbot, request data, and session key.
    6. Sends a post-create signal for the chatbot request.

    Parameters
    ----------
    chatbot_id : int
        The primary key of the ChatBot instance for which the request is being created.
    request_data : dict
        The data associated with the chatbot request. Should include all relevant request fields.

    Signals
    -------
    pre_create_chatbot_request : django.dispatch.Signal
        Sent before the ChatBotRequests record is created.
    post_create_chatbot_request : django.dispatch.Signal
        Sent after the ChatBotRequests record is created.

    Raises
    ------
    ChatBot.DoesNotExist
        If the ChatBot with the given ID does not exist.
    Exception
        Any exception raised during the creation process will trigger a retry according to Celery settings.
    """

    task_id = create_chatbot_request.request.id
    pre_create_chatbot_request.send(
        sender=create_chatbot_request, chatbot_id=chatbot_id, request_data=request_data, task_id=task_id
    )
    logger.info(
        "%s - chatbot %s task_id: %s received request data: %s",
        logger_prefix + f".{create_chatbot_request.__name__}() task_id: %s",
        chatbot_id,
        task_id,
        request_data,
    )
    chatbot = ChatBot.objects.get(id=chatbot_id)
    session_key = request_data.get(SMARTER_CHAT_SESSION_KEY_NAME)
    ChatBotRequests.objects.create(chatbot=chatbot, request=request_data, session_key=session_key)
    post_create_chatbot_request.send(
        sender=create_chatbot_request, chatbot_id=chatbot_id, request_data=request_data, task_id=task_id
    )
