"""Django Signal Receivers for chatbot."""

# pylint: disable=W0613,C0115
import json
import logging

from django.dispatch import receiver
from django.http import HttpRequest

from smarter.common.helpers.console_helpers import formatted_text

from .models import ChatBot
from .signals import (
    chatbot_called,
    chatbot_dns_failed,
    chatbot_dns_verification_initiated,
    chatbot_dns_verification_status_changed,
    chatbot_dns_verified,
)
from .tasks import create_chatbot_request


logger = logging.getLogger(__name__)


@receiver(chatbot_dns_verification_status_changed, dispatch_uid="chatbot_dns_verification_status_changed")
def handle_chatbot_dns_verification_status_changed(sender, **kwargs):
    """Handle chatbot_dns_verification_status_changed signal."""

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info(
        "%s - %s: %s",
        formatted_text("chatbot_dns_verification_status_changed"),
        chatbot.hostname,
        chatbot.dns_verification_status,
    )


@receiver(chatbot_dns_verification_initiated, dispatch_uid="chatbot_dns_verification_initiated")
def handle_chatbot_dns_verification_initiated(sender, **kwargs):
    """Handle chatbot_dns_verification_initiated signal."""

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s - %s", formatted_text("chatbot_dns_verification_initiated"), chatbot.hostname)


@receiver(chatbot_dns_verified, dispatch_uid="chatbot_dns_verified")
def handle_chatbot_dns_verified(sender, **kwargs):
    """Handle chatbot_dns_verified signal."""

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s - %s", formatted_text("chatbot_dns_verified"), chatbot.hostname)


@receiver(chatbot_dns_failed, dispatch_uid="chatbot_dns_failed")
def handle_chatbot_dns_failed(sender, **kwargs):
    """Handle chatbot_dns_failed signal."""

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s - %s", formatted_text("chatbot_dns_failed"), chatbot.hostname)


@receiver(chatbot_called, dispatch_uid="chatbot_called")
def handle_chatbot_called(sender, **kwargs):
    """Handle chatbot_called signal."""

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s - %s", formatted_text("chatbot_called"), chatbot.hostname)

    request: HttpRequest = kwargs.get("request")
    try:
        request_data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("handle_chatbot_called() received an empty or invalid request body from %s", chatbot.hostname)
        request_data = {
            "JSONDecodeError": "received an empty or invalid request body",
        }

    create_chatbot_request.delay(chatbot.id, request_data)
