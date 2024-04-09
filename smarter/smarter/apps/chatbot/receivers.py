# -*- coding: utf-8 -*-
"""Django Signal Receivers for chatbot."""
# pylint: disable=W0613,C0115
import json
import logging

from django.dispatch import receiver
from django.http import HttpRequest

from smarter.common.console_helpers import formatted_text

from .models import ChatBot
from .signals import chatbot_called
from .tasks import create_chatbot_request


logger = logging.getLogger(__name__)


@receiver(chatbot_called, dispatch_uid="chatbot_called")
def handle_chatbot_called(sender, **kwargs):
    """Handle chatbot_called signal."""

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s signal received for chatbot_called %s", formatted_text("chatbot_called"), chatbot.hostname)

    request: HttpRequest = kwargs.get("request")
    try:
        request_data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("JSONDecodeError raised while attempting to extract request body from %s", chatbot.hostname)
        request_data = {
            "JSONDecodeError": "JSONDecodeError raised while attempting to extract request body",
        }

    create_chatbot_request.delay(chatbot.id, request_data)
