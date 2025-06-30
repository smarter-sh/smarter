"""Django Signal Receivers for chatbot."""

# pylint: disable=W0613,C0115
import json
import logging
from typing import Optional

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.http import HttpRequest

from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.signals import plugin_deleting
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotFunctions,
    ChatBotPlugin,
    ChatBotRequests,
)
from .signals import (
    chatbot_called,
    chatbot_deploy_failed,
    chatbot_deploy_status_changed,
    chatbot_deployed,
    chatbot_dns_failed,
    chatbot_dns_verification_initiated,
    chatbot_dns_verification_status_changed,
    chatbot_dns_verified,
    chatbot_undeployed,
    post_create_chatbot_request,
    post_create_custom_domain_dns_record,
    post_delete_default_api,
    post_deploy_custom_api,
    post_deploy_default_api,
    post_destroy_domain_A_record,
    post_register_custom_domain,
    post_undeploy_default_api,
    post_verify_certificate,
    post_verify_custom_domain,
    post_verify_domain,
    pre_create_chatbot_request,
    pre_create_custom_domain_dns_record,
    pre_delete_default_api,
    pre_deploy_custom_api,
    pre_deploy_default_api,
    pre_destroy_domain_A_record,
    pre_register_custom_domain,
    pre_undeploy_default_api,
    pre_verify_certificate,
    pre_verify_custom_domain,
    pre_verify_domain,
)
from .tasks import (
    create_chatbot_request,
    delete_default_api,
    deploy_default_api,
    undeploy_default_api,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING)
        and level <= logging.INFO
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

module_prefix = "smarter.apps.chatbot.receivers"


@receiver(plugin_deleting, dispatch_uid=module_prefix + ".plugin_deleting")
def handle_plugin_deleting(sender, plugin, plugin_meta: PluginMeta, **kwargs):
    """Handle plugin deleting signal."""
    logger.info(
        "%s %s is being deleted. Pruning its usage records.",
        formatted_text("smarter.apps.chatbot.receivers.plugin_deleting"),
        plugin_meta.name,
    )
    ChatBotPlugin.objects.filter(plugin_meta=plugin_meta).delete()
    logger.info(
        "%s %s ChatBotPlugin records deleted.",
        formatted_text("smarter.apps.chatbot.receivers.plugin_deleting"),
        plugin_meta.name,
    )
    logger.info(
        "%s %s has been pruned from all chatbot usage records.",
        formatted_text("smarter.apps.chatbot.receivers.plugin_deleting"),
        plugin_meta.name,
    )


@receiver(chatbot_deploy_failed, dispatch_uid="chatbot_deploy_failed")
def handle_chatbot_deploy_failed(sender, **kwargs):
    """Handle chatbot_deploy_failed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_deploy_failed()")
    chatbot: Optional[ChatBot] = kwargs.get("chatbot")
    logger.error("%s - %s", prefix, chatbot.hostname if chatbot else "No chatbot instance provided")
    if chatbot:
        undeploy_default_api.delay(chatbot_id=chatbot.id)


@receiver(post_save, sender=ChatBot)
def chatbot_saved(sender, instance: ChatBot, created: bool, **kwargs):
    """
    create the default API for the chatbot.
    """
    prefix = formatted_text(f"{module_prefix}.chatbot_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.url)
    else:
        logger.info("%s - updated %s", prefix, instance.url)


@receiver(pre_delete, sender=ChatBot)
def chatbot_deleted(sender, instance: ChatBot, **kwargs):
    """
    delete the default API for the chatbot.
    """
    chatbot: ChatBot = instance
    prefix = formatted_text(f"{module_prefix}.chatbot_deleted()")
    logger.info("%s - %s", prefix, instance.url)
    delete_default_api.delay(url=chatbot.url, account_number=chatbot.account.account_number, name=chatbot.name)


@receiver(pre_delete, sender=ChatBotPlugin)
def chatbot_plugin_deleted(sender, instance: ChatBotPlugin, **kwargs):
    """
    Log deletion of ChatBotPlugin.
    """
    prefix = formatted_text(f"{module_prefix}.chatbot_plugin_deleted()")
    logger.info("%s - deleting plugin %s for chatbot %s", prefix, instance.plugin_meta, instance.chatbot)


@receiver(post_save, sender=ChatBotCustomDomain)
def chatbot_custom_domain_saved(sender, instance: ChatBotCustomDomain, created: bool, **kwargs):
    """
    Log creation or update of ChatBotCustomDomain.
    """
    prefix = formatted_text(f"{module_prefix}.chatbot_custom_domain_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.domain_name)
    else:
        logger.info("%s - updated %s", prefix, instance.domain_name)


@receiver(post_save, sender=ChatBotCustomDomainDNS)
def chatbot_custom_domain_dns_saved(sender, instance: ChatBotCustomDomainDNS, created: bool, **kwargs):
    """
    Log creation or update of ChatBotCustomDomainDNS.
    """
    prefix = formatted_text(f"{module_prefix}.chatbot_custom_domain_dns_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.custom_domain.domain_name)
    else:
        logger.info("%s - updated %s", prefix, instance.custom_domain.domain_name)


@receiver(post_save, sender=ChatBotAPIKey)
def chatbot_api_key_saved(sender, instance: ChatBotAPIKey, created: bool, **kwargs):
    """
    Log creation or update of ChatBotAPIKey.
    """
    prefix = formatted_text(f"{module_prefix}.chatbot_api_key_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.api_key)
    else:
        logger.info("%s - updated %s", prefix, instance.api_key)


@receiver(post_save, sender=ChatBotPlugin)
def chatbot_plugin_saved(sender, instance: ChatBotPlugin, created: bool, **kwargs):
    """
    Log creation or update of ChatBotPlugin.
    """
    prefix = formatted_text(f"{module_prefix}.chatbot_plugin_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.plugin_meta.name)
    else:
        logger.info("%s - updated %s", prefix, instance.plugin_meta.name)


@receiver(post_save, sender=ChatBotFunctions)
def chatbot_functions_saved(sender, instance: ChatBotFunctions, created: bool, **kwargs):
    """
    Log creation or update of ChatBotFunctions.
    """
    prefix = formatted_text(f"{module_prefix}.chatbot_functions_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.name)
    else:
        logger.info("%s - updated %s", prefix, instance.name)


@receiver(post_save, sender=ChatBotRequests)
def chatbot_requests_saved(sender, instance: ChatBotRequests, created: bool, **kwargs):
    """
    Log creation or update of ChatBotRequests.
    """
    prefix = formatted_text(f"{module_prefix}.chatbot_requests_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.session_key)
    else:
        logger.info("%s - updated %s", prefix, instance.session_key)


###############################################################################
# Custom Signal handlers for ChatBot deployment and DNS verification status changes
###############################################################################


@receiver(chatbot_deploy_status_changed, dispatch_uid="chatbot_deploy_status_changed")
def handle_chatbot_deploy_status_changed(sender, **kwargs):
    """Handle chatbot_deploy_status_changed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_deploy_status_changed()")

    chatbot: Optional[ChatBot] = kwargs.get("chatbot")
    logger.info(
        "%s - %s: %s",
        prefix,
        chatbot.url if chatbot else "No chatbot instance provided",
        chatbot.dns_verification_status if chatbot else "N/A",
    )


@receiver(chatbot_undeployed, dispatch_uid="chatbot_undeployed")
def handle_chatbot_undeployed(sender, **kwargs):
    """Handle chatbot_undeployed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_undeployed()")

    chatbot: Optional[ChatBot] = kwargs.get("chatbot")
    logger.info("%s - %s", prefix, chatbot.hostname if chatbot else "No chatbot instance provided")
    if chatbot:
        undeploy_default_api.delay(chatbot_id=chatbot.id)


@receiver(chatbot_deployed, dispatch_uid="chatbot_deployed")
def handle_chatbot_deployed(sender, **kwargs):
    """Handle chatbot_deployed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_deployed()")

    chatbot: Optional[ChatBot] = kwargs.get("chatbot")
    logger.info("%s signal received - %s", prefix, chatbot.hostname if chatbot else "No chatbot instance provided")
    if chatbot:
        deploy_default_api.delay(chatbot_id=chatbot.id)


@receiver(chatbot_dns_verification_status_changed, dispatch_uid="chatbot_dns_verification_status_changed")
def handle_chatbot_dns_verification_status_changed(sender, **kwargs):
    """Handle chatbot_dns_verification_status_changed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_deployed()")

    chatbot: Optional[ChatBot] = kwargs.get("chatbot")
    logger.info(
        "%s - %s: %s",
        prefix,
        chatbot.hostname if chatbot else "No chatbot instance provided",
        chatbot.dns_verification_status if chatbot else "N/A",
    )


@receiver(chatbot_dns_verification_initiated, dispatch_uid="chatbot_dns_verification_initiated")
def handle_chatbot_dns_verification_initiated(sender, **kwargs):
    """Handle chatbot_dns_verification_initiated signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_dns_verification_initiated()")

    chatbot: Optional[ChatBot] = kwargs.get("chatbot")
    logger.info("%s - %s", prefix, chatbot.hostname if chatbot else "No chatbot instance provided")


@receiver(chatbot_dns_verified, dispatch_uid="chatbot_dns_verified")
def handle_chatbot_dns_verified(sender, **kwargs):
    """Handle chatbot_dns_verified signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_dns_verified()")

    chatbot: Optional[ChatBot] = kwargs.get("chatbot")
    logger.info("%s - %s", prefix, chatbot.hostname if chatbot else "No chatbot instance provided")


@receiver(chatbot_dns_failed, dispatch_uid="chatbot_dns_failed")
def handle_chatbot_dns_failed(sender, **kwargs):
    """Handle chatbot_dns_failed signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_dns_failed()")

    chatbot: Optional[ChatBot] = kwargs.get("chatbot")
    logger.info("%s - %s", prefix, chatbot.hostname if chatbot else "No chatbot instance provided")


@receiver(chatbot_called, dispatch_uid="chatbot_called")
def handle_chatbot_called(sender, **kwargs):
    """Handle chatbot_called signal."""
    prefix = formatted_text(f"{module_prefix}.handle_chatbot_called()")

    chatbot: Optional[ChatBot] = kwargs.get("chatbot")
    if waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_HELPER_LOGGING):
        logger.info("%s - %s", prefix, chatbot.hostname if chatbot else "No chatbot instance provided")

    request: Optional[HttpRequest] = kwargs.get("request")
    try:
        request_data = json.loads(request.body) if request and request.body else None
        if chatbot and request_data:
            create_chatbot_request.delay(chatbot.id, request_data)
    except json.JSONDecodeError:
        logger.warning(
            "%s received an empty or invalid request body from %s",
            prefix,
            chatbot.hostname if chatbot else "No chatbot instance provided",
        )
        request_data = {
            "JSONDecodeError": "received an empty or invalid request body",
        }


###############################################################################
# custom task receivers
###############################################################################


@receiver(pre_verify_certificate, dispatch_uid="pre_verify_certificate")
def handle_pre_verify_certificate(sender, **kwargs):
    """Handle pre_verify_certificate signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_verify_certificate()")
    certificate_arn = kwargs.get("certificate_arn")
    logger.info("%s - certificate_arn: %s", prefix, certificate_arn)


@receiver(post_verify_certificate, dispatch_uid="post_verify_certificate")
def handle_post_verify_certificate(sender, **kwargs):
    """Handle post_verify_certificate signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_verify_certificate()")
    certificate_arn = kwargs.get("certificate_arn")
    logger.info("%s - certificate_arn: %s", prefix, certificate_arn)


@receiver(pre_create_chatbot_request, dispatch_uid="pre_create_chatbot_request")
def handle_pre_create_chatbot_request(sender, **kwargs):
    """Handle pre_create_chatbot_request signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_create_chatbot_request()")
    chatbot_id = kwargs.get("chatbot_id")
    request_data = kwargs.get("request_data")
    request_data = json.loads(request_data) if isinstance(request_data, str) else request_data
    logger.info("%s - chatbot_id: %s, request_data: %s", prefix, chatbot_id, formatted_json(request_data))


@receiver(post_create_chatbot_request, dispatch_uid="post_create_chatbot_request")
def handle_post_create_chatbot_request(sender, **kwargs):
    """Handle post_create_chatbot_request signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_create_chatbot_request()")
    chatbot_id = kwargs.get("chatbot_id")
    request_data = kwargs.get("request_data")
    request_data = json.loads(request_data) if isinstance(request_data, str) else request_data
    logger.info("%s - chatbot_id: %s, request_data: %s", prefix, chatbot_id, formatted_json(request_data))


@receiver(pre_register_custom_domain, dispatch_uid="pre_register_custom_domain")
def handle_pre_register_custom_domain(sender, **kwargs):
    """Handle pre_register_custom_domain signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_register_custom_domain()")
    account_id = kwargs.get("account_id")
    domain_name = kwargs.get("domain_name")
    logger.info("%s - account_id: %s, domain_name: %s", prefix, account_id, domain_name)


@receiver(post_register_custom_domain, dispatch_uid="post_register_custom_domain")
def handle_post_register_custom_domain(sender, **kwargs):
    """Handle post_register_custom_domain signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_register_custom_domain()")
    account_id = kwargs.get("account_id")
    domain_name = kwargs.get("domain_name")
    logger.info("%s - account_id: %s, domain_name: %s", prefix, account_id, domain_name)


@receiver(pre_create_custom_domain_dns_record, dispatch_uid="pre_create_custom_domain_dns_record")
def handle_pre_create_custom_domain_dns_record(sender, **kwargs):
    """Handle pre_create_custom_domain_dns_record signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_create_custom_domain_dns_record()")
    chatbot_custom_domain_id = kwargs.get("chatbot_custom_domain_id")
    record_name = kwargs.get("record_name")
    record_type = kwargs.get("record_type")
    record_value = kwargs.get("record_value")
    record_ttl = kwargs.get("record_ttl")
    logger.info(
        "%s - chatbot_custom_domain_id: %s, record_name: %s, record_type: %s, record_value: %s, record_ttl: %s",
        prefix,
        chatbot_custom_domain_id,
        record_name,
        record_type,
        record_value,
        record_ttl,
    )


@receiver(post_create_custom_domain_dns_record, dispatch_uid="post_create_custom_domain_dns_record")
def handle_post_create_custom_domain_dns_record(sender, **kwargs):
    """Handle post_create_custom_domain_dns_record signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_create_custom_domain_dns_record()")
    chatbot_custom_domain_id = kwargs.get("chatbot_custom_domain_id")
    record_name = kwargs.get("record_name")
    record_type = kwargs.get("record_type")
    record_value = kwargs.get("record_value")
    record_ttl = kwargs.get("record_ttl")
    logger.info(
        "%s - chatbot_custom_domain_id: %s, record_name: %s, record_type: %s, record_value: %s, record_ttl: %s",
        prefix,
        chatbot_custom_domain_id,
        record_name,
        record_type,
        record_value,
        record_ttl,
    )


@receiver(pre_verify_custom_domain, dispatch_uid="pre_verify_custom_domain")
def handle_pre_verify_custom_domain(sender, **kwargs):
    """Handle pre_verify_custom_domain signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_verify_custom_domain()")
    hosted_zone_id = kwargs.get("hosted_zone_id")
    logger.info("%s - hosted_zone_id: %s", prefix, hosted_zone_id)


@receiver(post_verify_custom_domain, dispatch_uid="post_verify_custom_domain")
def handle_post_verify_custom_domain(sender, **kwargs):
    """Handle post_verify_custom_domain signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_verify_custom_domain()")
    hosted_zone_id = kwargs.get("hosted_zone_id")
    logger.info("%s - hosted_zone_id: %s", prefix, hosted_zone_id)


@receiver(pre_verify_domain, dispatch_uid="pre_verify_domain")
def handle_pre_verify_domain(sender, **kwargs):
    """Handle pre_verify_domain signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_verify_domain()")
    domain_name = kwargs.get("domain_name")
    record_type = kwargs.get("record_type")
    logger.info("%s - domain_name: %s, record_type: %s", prefix, domain_name, record_type)


@receiver(post_verify_domain, dispatch_uid="post_verify_domain")
def handle_post_verify_domain(sender, **kwargs):
    """Handle post_verify_domain signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_verify_domain()")
    domain_name = kwargs.get("domain_name")
    record_type = kwargs.get("record_type")
    logger.info("%s - domain_name: %s, record_type: %s", prefix, domain_name, record_type)


@receiver(pre_destroy_domain_A_record, dispatch_uid="pre_destroy_domain_A_record")
def handle_pre_destroy_domain_A_record(sender, **kwargs):
    """Handle pre_destroy_domain_A_record signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_destroy_domain_A_record()")
    hostname = kwargs.get("hostname")
    api_host_domain = kwargs.get("api_host_domain")
    logger.info("%s - hostname: %s, api_host_domain: %s", prefix, hostname, api_host_domain)


@receiver(post_destroy_domain_A_record, dispatch_uid="post_destroy_domain_A_record")
def handle_post_destroy_domain_A_record(sender, **kwargs):
    """Handle post_destroy_domain_A_record signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_destroy_domain_A_record()")
    hostname = kwargs.get("hostname")
    api_host_domain = kwargs.get("api_host_domain")
    logger.info("%s - hostname: %s, api_host_domain: %s", prefix, hostname, api_host_domain)


@receiver(pre_deploy_default_api, dispatch_uid="pre_deploy_default_api")
def handle_pre_deploy_default_api(sender, **kwargs):
    """Handle pre_deploy_default_api signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_deploy_default_api()")
    chatbot_id = kwargs.get("chatbot_id")
    with_domain_verification = kwargs.get("with_domain_verification")
    logger.info("%s - chatbot_id: %s, with_domain_verification: %s", prefix, chatbot_id, with_domain_verification)


@receiver(post_deploy_default_api, dispatch_uid="post_deploy_default_api")
def handle_post_deploy_default_api(sender, **kwargs):
    """Handle post_deploy_default_api signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_deploy_default_api()")
    chatbot_id = kwargs.get("chatbot_id")
    with_domain_verification = kwargs.get("with_domain_verification")
    logger.info("%s - chatbot_id: %s, with_domain_verification: %s", prefix, chatbot_id, with_domain_verification)


@receiver(pre_undeploy_default_api, dispatch_uid="pre_undeploy_default_api")
def handle_pre_undeploy_default_api(sender, **kwargs):
    """Handle pre_undeploy_default_api signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_undeploy_default_api()")
    chatbot_id = kwargs.get("chatbot_id")
    logger.info("%s - chatbot_id: %s", prefix, chatbot_id)


@receiver(post_undeploy_default_api, dispatch_uid="post_undeploy_default_api")
def handle_post_undeploy_default_api(sender, **kwargs):
    """Handle post_undeploy_default_api signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_undeploy_default_api()")
    chatbot_id = kwargs.get("chatbot_id")
    logger.info("%s - chatbot_id: %s", prefix, chatbot_id)


@receiver(pre_delete_default_api, dispatch_uid="pre_delete_default_api")
def handle_pre_delete_default_api(sender, **kwargs):
    """Handle pre_delete_default_api signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_delete_default_api()")
    url = kwargs.get("url")
    account_number = kwargs.get("account_number")
    name = kwargs.get("name")
    logger.info("%s - url: %s, account_number: %s, name: %s", prefix, url, account_number, name)


@receiver(post_delete_default_api, dispatch_uid="post_delete_default_api")
def handle_post_delete_default_api(sender, **kwargs):
    """Handle post_delete_default_api signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_delete_default_api()")
    url = kwargs.get("url")
    account_number = kwargs.get("account_number")
    name = kwargs.get("name")
    logger.info("%s - url: %s, account_number: %s, name: %s", prefix, url, account_number, name)


@receiver(pre_deploy_custom_api, dispatch_uid="pre_deploy_custom_api")
def handle_pre_deploy_custom_api(sender, **kwargs):
    """Handle pre_deploy_custom_api signal."""
    prefix = formatted_text(f"{module_prefix}.handle_pre_deploy_custom_api()")
    chatbot_id = kwargs.get("chatbot_id")
    logger.info("%s - chatbot_id: %s", prefix, chatbot_id)


@receiver(post_deploy_custom_api, dispatch_uid="post_deploy_custom_api")
def handle_post_deploy_custom_api(sender, **kwargs):
    """Handle post_deploy_custom_api signal."""
    prefix = formatted_text(f"{module_prefix}.handle_post_deploy_custom_api()")
    chatbot_id = kwargs.get("chatbot_id")
    logger.info("%s - chatbot_id: %s", prefix, chatbot_id)
