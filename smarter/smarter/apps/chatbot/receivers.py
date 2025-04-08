"""Django Signal Receivers for chatbot."""

# pylint: disable=W0613,C0115
import json
import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.http import HttpRequest

from smarter.common.const import SmarterWaffleSwitches
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle

from .models import ChatBot
from .signals import (
    chatbot_called,
    chatbot_deleted,
    chatbot_deploy_failed,
    chatbot_deploy_status_changed,
    chatbot_deployed,
    chatbot_dns_failed,
    chatbot_dns_verification_initiated,
    chatbot_dns_verification_status_changed,
    chatbot_dns_verified,
    chatbot_undeployed,
)
from .tasks import (
    create_chatbot_request,
    delete_default_api,
    deploy_default_api,
    undeploy_default_api,
)


logger = logging.getLogger(__name__)
module_prefix = "smarter.apps.chatbot.receivers"


@receiver(chatbot_deploy_failed, dispatch_uid="chatbot_deploy_failed")
def handle_chatbot_deploy_failed(sender, **kwargs):
    """Handle chatbot_deploy_failed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_deploy_failed()")
    chatbot: ChatBot = kwargs.get("chatbot")
    logger.error("%s - %s", prefix, chatbot.hostname)
    undeploy_default_api.delay(chatbot_id=chatbot.id)


@receiver(post_delete, sender=ChatBot)
def django_chatbot_deleted(sender, instance, **kwargs):
    """
    Handle django post_delete signal for ChatBot model.
    Send our own chatbot_deleted signal.
    """
    prefix = formatted_text(f"{module_prefix}.django_chatbot_deleted()")
    logger.info("%s - %s", prefix, instance.url)
    chatbot_deleted.send(sender="smarter.apps.chatbot.receivers.django_chatbot_deleted()", chatbot=instance)


@receiver(chatbot_deleted, dispatch_uid="chatbot_deleted")
def handle_chatbot_deleted(sender, **kwargs):
    """Handle chatbot_deleted signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_deleted()")

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s - %s", prefix, chatbot.url)
    delete_default_api.delay(url=chatbot.url, account_number=chatbot.account.account_number, name=chatbot.name)


@receiver(chatbot_deploy_status_changed, dispatch_uid="chatbot_deploy_status_changed")
def handle_chatbot_deploy_status_changed(sender, **kwargs):
    """Handle chatbot_deploy_status_changed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_deploy_status_changed()")

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info(
        "%s - %s: %s",
        prefix,
        chatbot.url,
        chatbot.dns_verification_status,
    )


@receiver(chatbot_undeployed, dispatch_uid="chatbot_undeployed")
def handle_chatbot_undeployed(sender, **kwargs):
    """Handle chatbot_undeployed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_undeployed()")

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s - %s", prefix, chatbot.hostname)
    undeploy_default_api.delay(chatbot_id=chatbot.id)


@receiver(chatbot_deployed, dispatch_uid="chatbot_deployed")
def handle_chatbot_deployed(sender, **kwargs):
    """Handle chatbot_deployed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_deployed()")

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s signal received - %s", prefix, chatbot.hostname)
    deploy_default_api.delay(chatbot_id=chatbot.id)


@receiver(chatbot_dns_verification_status_changed, dispatch_uid="chatbot_dns_verification_status_changed")
def handle_chatbot_dns_verification_status_changed(sender, **kwargs):
    """Handle chatbot_dns_verification_status_changed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_deployed()")

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info(
        "%s - %s: %s",
        prefix,
        chatbot.hostname,
        chatbot.dns_verification_status,
    )


@receiver(chatbot_dns_verification_initiated, dispatch_uid="chatbot_dns_verification_initiated")
def handle_chatbot_dns_verification_initiated(sender, **kwargs):
    """Handle chatbot_dns_verification_initiated signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_dns_verification_initiated()")

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s - %s", prefix, chatbot.hostname)


@receiver(chatbot_dns_verified, dispatch_uid="chatbot_dns_verified")
def handle_chatbot_dns_verified(sender, **kwargs):
    """Handle chatbot_dns_verified signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_dns_verified()")

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s - %s", prefix, chatbot.hostname)


@receiver(chatbot_dns_failed, dispatch_uid="chatbot_dns_failed")
def handle_chatbot_dns_failed(sender, **kwargs):
    """Handle chatbot_dns_failed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_dns_failed()")

    chatbot: ChatBot = kwargs.get("chatbot")
    logger.info("%s - %s", prefix, chatbot.hostname)


@receiver(chatbot_called, dispatch_uid="chatbot_called")
def handle_chatbot_called(sender, **kwargs):
    """Handle chatbot_called signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_called()")

    chatbot: ChatBot = kwargs.get("chatbot")
    if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_HELPER_LOGGING):
        logger.info("%s - %s", prefix, chatbot.hostname)

    request: HttpRequest = kwargs.get("request")
    try:
        request_data = json.loads(request.body)
        create_chatbot_request.delay(chatbot.id, request_data)
    except json.JSONDecodeError:
        logger.warning("%s received an empty or invalid request body from %s", prefix, chatbot.hostname)
        request_data = {
            "JSONDecodeError": "received an empty or invalid request body",
        }
