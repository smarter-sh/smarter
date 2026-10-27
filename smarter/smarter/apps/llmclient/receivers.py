"""Django Signal Receivers for llmclient."""

# pylint: disable=W0613,C0115
from typing import Optional

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from smarter.apps.llmtool.models import PluginMeta
from smarter.apps.llmtool.signals import plugin_deleting
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.utils import mask_identifier
from smarter.lib import json, logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.broker import AbstractBroker

from .const import (
    CUSTOM_DOMAIN_LISTVIEW_CACHE_KIND,
    CUSTOM_DOMAIN_LISTVIEW_CACHE_MODELS,
    LLMCLIENT_LISTVIEW_CACHE_KIND,
    LLMCLIENT_LISTVIEW_CACHE_MODELS,
)
from .models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
    LLMClientExtensions,
    LLMClientMCPClients,
    LLMClientPlugin,
    LLMClientRequests,
    invalidate_cached_llmclient_by_hosts,
)
from .models.utils import invalidate_cached_llmclient_tool_counts
from .serializers import LLMClientSerializer
from .signals import (
    broker_ready,
    llmclient_called,
    llmclient_deploy,
    llmclient_deploy_failed,
    llmclient_deploy_status_changed,
    llmclient_deployed,
    llmclient_dns_failed,
    llmclient_dns_verification_initiated,
    llmclient_dns_verification_status_changed,
    llmclient_dns_verified,
    llmclient_undeploy,
    post_create_custom_domain_dns_record,
    post_create_llmclient_request,
    post_delete_default_api,
    post_deploy_custom_api,
    post_deploy_default_api,
    post_destroy_domain_A_record,
    post_register_custom_domain,
    post_undeploy_default_api,
    post_verify_certificate,
    post_verify_custom_domain,
    post_verify_domain,
    pre_create_custom_domain_dns_record,
    pre_create_llmclient_request,
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
    create_llmclient_request,
    delete_default_api,
    deploy_custom_api,
    deploy_default_api,
    undeploy_default_api,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

module_prefix = __name__


@receiver(plugin_deleting, dispatch_uid=module_prefix + ".plugin_deleting")
def handle_plugin_deleting(sender, plugin, plugin_meta: PluginMeta, **kwargs):
    """Handle plugin deleting signal."""
    logger.info(
        "%s %s is being deleted. Pruning its usage records.",
        f"{logging.SmarterFormattedText.text(module_prefix)}.plugin_deleting",
        plugin_meta.name,
    )


@receiver(llmclient_deploy_failed, dispatch_uid="llmclient_deploy_failed")
def handle_llmclient_deploy_failed(sender, **kwargs):
    """Handle llmclient_deploy_failed signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_deploy_failed()"
    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.error("%s %s", prefix, llmclient.hostname if llmclient else "No llmclient instance provided")


@receiver(post_save, sender=LLMClient)
def llmclient_saved(sender, instance: LLMClient, created: bool, **kwargs):
    """Create the default API for the llmclient."""

    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_saved()"
    # its hosts may have changed, e.g. when it is renamed.
    invalidate_cached_llmclient_by_hosts(instance)
    logger.info("%s %s %s", prefix, "created" if created else "updated", instance.url)
    # the serialized LLMClient, with its tools, costs several queries, so only when it will be logged.
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s %s", prefix, logging.SmarterFormattedText.json(LLMClientSerializer(instance).data))


@receiver(pre_delete, sender=LLMClient)
def llmclient_deleted(sender, instance: LLMClient, **kwargs):
    """Delete the default API for the llmclient."""
    llmclient: LLMClient = instance
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_deleted()"
    logger.info("%s %s", prefix, instance.url)
    invalidate_cached_llmclient_by_hosts(llmclient)
    # the task is passed the account number, read now, because the llmclient may be deleted
    # with its account, which then no longer exists when the task runs. It is queued when the
    # deletion is committed, so that a deletion that is rolled back deletes no resources.
    kwargs = {
        "name": llmclient.name,
        "account_number": llmclient.user_profile.account.account_number,  # type: ignore[union-attr]
        "api_url": llmclient.default_url,
    }
    transaction.on_commit(lambda: delete_default_api.delay(**kwargs))


def llmclient_tools_changed(sender, instance, **kwargs):
    """
    Invalidate an LLMClient's cached tool counts when one of its plugins, extensions or MCPClients is added or removed.

    See :func:`smarter.apps.llmclient.models.utils.get_cached_llmclient_tool_counts`.
    """
    invalidate_cached_llmclient_tool_counts(getattr(instance, "llmclient_id", None))


for _tool_link in (LLMClientPlugin, LLMClientExtensions, LLMClientMCPClients):
    post_save.connect(
        llmclient_tools_changed, sender=_tool_link, dispatch_uid=f"{module_prefix}.{_tool_link.__name__}.post_save"
    )
    post_delete.connect(
        llmclient_tools_changed, sender=_tool_link, dispatch_uid=f"{module_prefix}.{_tool_link.__name__}.post_delete"
    )


@receiver(pre_delete, sender=LLMClientPlugin)
def llmclient_plugin_deleted(sender, instance: LLMClientPlugin, **kwargs):
    """Log deletion of LLMClientPlugin."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_plugin_deleted()"
    logger.info("%s deleting plugin %s for llmclient %s", prefix, instance.plugin_meta, instance.llmclient)


@receiver(post_save, sender=LLMClientCustomDomain)
def llmclient_custom_domain_saved(sender, instance: LLMClientCustomDomain, created: bool, **kwargs):
    """Log creation or update of LLMClientCustomDomain."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_custom_domain_saved()"
    if created:
        logger.info("%s created %s", prefix, instance.domain_name)
    else:
        logger.info("%s updated %s", prefix, instance.domain_name)


@receiver(post_save, sender=LLMClientCustomDomainDNS)
def llmclient_custom_domain_dns_saved(sender, instance: LLMClientCustomDomainDNS, created: bool, **kwargs):
    """Log creation or update of LLMClientCustomDomainDNS."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_custom_domain_dns_saved()"
    if created:
        logger.info("%s created %s", prefix, instance.custom_domain.domain_name)
    else:
        logger.info("%s updated %s", prefix, instance.custom_domain.domain_name)


@receiver(post_save, sender=LLMClientAPIKey)
def llmclient_api_key_saved(sender, instance: LLMClientAPIKey, created: bool, **kwargs):
    """Log creation or update of LLMClientAPIKey."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_api_key_saved()"
    if created:
        logger.info("%s created %s", prefix, instance.api_key)
    else:
        logger.info("%s updated %s", prefix, instance.api_key)


@receiver(post_save, sender=LLMClientPlugin)
def llmclient_plugin_saved(sender, instance: LLMClientPlugin, created: bool, **kwargs):
    """Log creation or update of LLMClientPlugin."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_plugin_saved()"
    if created:
        logger.info("%s created %s", prefix, instance.plugin_meta.name)
    else:
        logger.info("%s updated %s", prefix, instance.plugin_meta.name)


@receiver(post_save, sender=LLMClientExtensions)
def llmclient_extensions_saved(sender, instance: LLMClientExtensions, created: bool, **kwargs):
    """Log creation or update of LLMClientExtensions."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_extensions_saved()"
    if created:
        logger.info("%s created %s", prefix, instance.extension.slug)
    else:
        logger.info("%s updated %s", prefix, instance.extension.slug)


@receiver(post_save, sender=LLMClientRequests)
def llmclient_requests_saved(sender, instance: LLMClientRequests, created: bool, **kwargs):
    """Log creation or update of LLMClientRequests."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_requests_saved()"
    if created:
        logger.info("%s created session %s", prefix, mask_identifier(instance.session_key))
    else:
        logger.info("%s updated session %s", prefix, mask_identifier(instance.session_key))


###############################################################################
# Custom Signal handlers for LLMClient deployment and DNS verification status changes
###############################################################################


@receiver(llmclient_deploy_status_changed, dispatch_uid="llmclient_deploy_status_changed")
def handle_llmclient_deploy_status_changed(sender, **kwargs):
    """Handle llmclient_deploy_status_changed signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_deploy_status_changed()"

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info(
        "%s %s: %s",
        prefix,
        llmclient.url if llmclient else "No llmclient instance provided",
        llmclient.dns_verification_status if llmclient else "N/A",
    )


@receiver(llmclient_undeploy, dispatch_uid="llmclient_undeploy")
def handle_llmclient_undeploy(sender, llmclient: Optional[LLMClient] = None, **kwargs):
    """Handle llmclient_undeploy signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_undeploy()"

    logger.info("%s %s", prefix, llmclient if llmclient else "No llmclient instance provided")
    if llmclient:
        undeploy_default_api.delay(llmclient_id=llmclient.id)  # type: ignore[union-attr]


@receiver(llmclient_deploy, dispatch_uid="llmclient_deploy")
def handle_llmclient_deploy(sender, **kwargs):
    """Handle llmclient_deploy signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_deploy()"

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info(
        "%s signal received - %s", prefix, llmclient.hostname if llmclient else "No llmclient instance provided"
    )
    if llmclient:
        logger.info("%s deploying llmclient - %s", prefix, llmclient.hostname)
        deploy_default_api.delay(llmclient_id=llmclient.id)  # type: ignore[union-attr]


@receiver(llmclient_deployed, dispatch_uid="llmclient_deployed")
def handle_llmclient_deployed(sender, **kwargs):
    """Handle llmclient_deployed signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_deployed()"

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info("%s %s", prefix, llmclient.hostname if llmclient else "No llmclient instance provided")
    # an llmclient with a verified custom domain is also served on its custom host.
    if llmclient and llmclient.custom_host:
        logger.info("%s deploying llmclient %s on %s", prefix, llmclient.name, llmclient.custom_host)
        deploy_custom_api.delay(llmclient_id=llmclient.id)  # type: ignore[union-attr]


@receiver(llmclient_dns_verification_status_changed, dispatch_uid="llmclient_dns_verification_status_changed")
def handle_llmclient_dns_verification_status_changed(sender, **kwargs):
    """Handle llmclient_dns_verification_status_changed signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_dns_verification_status_changed()"

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info(
        "%s %s: %s",
        prefix,
        llmclient.hostname if llmclient else "No llmclient instance provided",
        llmclient.dns_verification_status if llmclient else "N/A",
    )


@receiver(llmclient_dns_verification_initiated, dispatch_uid="llmclient_dns_verification_initiated")
def handle_llmclient_dns_verification_initiated(sender, **kwargs):
    """Handle llmclient_dns_verification_initiated signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_dns_verification_initiated()"

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info("%s %s", prefix, llmclient.hostname if llmclient else "No llmclient instance provided")


@receiver(llmclient_dns_verified, dispatch_uid="llmclient_dns_verified")
def handle_llmclient_dns_verified(sender, **kwargs):
    """Handle llmclient_dns_verified signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_dns_verified()"

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info("%s %s", prefix, llmclient.hostname if llmclient else "No llmclient instance provided")


@receiver(llmclient_dns_failed, dispatch_uid="llmclient_dns_failed")
def handle_llmclient_dns_failed(sender, **kwargs):
    """Handle llmclient_dns_failed signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_dns_failed()"

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info("%s %s", prefix, llmclient.hostname if llmclient else "No llmclient instance provided")


@receiver(llmclient_called, dispatch_uid="llmclient_called")
def handle_llmclient_called(sender, **kwargs):
    """Handle llmclient_called signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.llmclient_called()"

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info("%s %s", prefix, llmclient.hostname if llmclient else "No llmclient instance provided")

    request_data = kwargs.get("data")
    try:
        if llmclient and request_data:
            create_llmclient_request.delay(llmclient.id, request_data)
        else:
            logger.error(
                "%s Missing llmclient instance or request data. LLMClient: %s, Data: %s",
                prefix,
                llmclient.hostname if llmclient else "No llmclient instance provided",
                "Present" if request_data else "No data",
            )
    except json.JSONDecodeError:
        logger.warning(
            "%s received an empty or invalid request body from %s",
            prefix,
            llmclient.hostname if llmclient else "No llmclient instance provided",
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
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_verify_certificate()"
    certificate_arn = kwargs.get("certificate_arn")
    logger.info("%s certificate_arn: %s", prefix, certificate_arn)


@receiver(post_verify_certificate, dispatch_uid="post_verify_certificate")
def handle_post_verify_certificate(sender, **kwargs):
    """Handle post_verify_certificate signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_verify_certificate()"
    certificate_arn = kwargs.get("certificate_arn")
    logger.info("%s certificate_arn: %s", prefix, certificate_arn)


@receiver(pre_create_llmclient_request, dispatch_uid="pre_create_llmclient_request")
def handle_pre_create_llmclient_request(sender, **kwargs):
    """Handle pre_create_llmclient_request signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_create_llmclient_request()"
    llmclient_id = kwargs.get("llmclient_id")
    request_data = kwargs.get("request_data")
    request_data = json.loads(request_data) if isinstance(request_data, str) else request_data
    # the user's prompt is personal data, so it is logged at DEBUG only, and the
    # session key, which would let anyone continue the conversation, is masked.
    logger.debug(
        "%s llmclient_id: %s, request_data: %s",
        prefix,
        llmclient_id,
        logging.SmarterFormattedText.json(_masked_request_data(request_data)) if request_data else "No data",
    )


@receiver(post_create_llmclient_request, dispatch_uid="post_create_llmclient_request")
def handle_post_create_llmclient_request(sender, **kwargs):
    """Handle post_create_llmclient_request signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_create_llmclient_request()"
    llmclient_id = kwargs.get("llmclient_id")
    request_data = kwargs.get("request_data")
    request_data = json.loads(request_data) if isinstance(request_data, str) else request_data
    session_key = request_data.get(SMARTER_CHAT_SESSION_KEY_NAME) if isinstance(request_data, dict) else None
    logger.debug(
        "%s llmclient_id: %s, session_key: %s",
        prefix,
        llmclient_id,
        mask_identifier(session_key),
    )


def _masked_request_data(request_data):
    """
    Return a copy of a chat request's data, with its session key masked, for logging.

    :param request_data: The request data that the chat api received, usually a dict.
    :returns: A shallow copy of the dict with its session key masked, or ``request_data``
        unchanged when it isn't a dict.
    """
    if not isinstance(request_data, dict) or SMARTER_CHAT_SESSION_KEY_NAME not in request_data:
        return request_data
    return {**request_data, SMARTER_CHAT_SESSION_KEY_NAME: mask_identifier(request_data[SMARTER_CHAT_SESSION_KEY_NAME])}


@receiver(pre_register_custom_domain, dispatch_uid="pre_register_custom_domain")
def handle_pre_register_custom_domain(sender, **kwargs):
    """Handle pre_register_custom_domain signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_register_custom_domain()"
    account_id = kwargs.get("account_id")
    domain_name = kwargs.get("domain_name")
    logger.info("%s account_id: %s, domain_name: %s", prefix, account_id, domain_name)


@receiver(post_register_custom_domain, dispatch_uid="post_register_custom_domain")
def handle_post_register_custom_domain(sender, **kwargs):
    """Handle post_register_custom_domain signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_register_custom_domain()"
    account_id = kwargs.get("account_id")
    domain_name = kwargs.get("domain_name")
    logger.info("%s account_id: %s, domain_name: %s", prefix, account_id, domain_name)


@receiver(pre_create_custom_domain_dns_record, dispatch_uid="pre_create_custom_domain_dns_record")
def handle_pre_create_custom_domain_dns_record(sender, **kwargs):
    """Handle pre_create_custom_domain_dns_record signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_create_custom_domain_dns_record()"
    llmclient_custom_domain_id = kwargs.get("llmclient_custom_domain_id")
    record_name = kwargs.get("record_name")
    record_type = kwargs.get("record_type")
    record_value = kwargs.get("record_value")
    record_ttl = kwargs.get("record_ttl")
    logger.info(
        "%s llmclient_custom_domain_id: %s, record_name: %s, record_type: %s, record_value: %s, record_ttl: %s",
        prefix,
        llmclient_custom_domain_id,
        record_name,
        record_type,
        record_value,
        record_ttl,
    )


@receiver(post_create_custom_domain_dns_record, dispatch_uid="post_create_custom_domain_dns_record")
def handle_post_create_custom_domain_dns_record(sender, **kwargs):
    """Handle post_create_custom_domain_dns_record signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_create_custom_domain_dns_record()"
    llmclient_custom_domain_id = kwargs.get("llmclient_custom_domain_id")
    record_name = kwargs.get("record_name")
    record_type = kwargs.get("record_type")
    record_value = kwargs.get("record_value")
    record_ttl = kwargs.get("record_ttl")
    logger.info(
        "%s llmclient_custom_domain_id: %s, record_name: %s, record_type: %s, record_value: %s, record_ttl: %s",
        prefix,
        llmclient_custom_domain_id,
        record_name,
        record_type,
        record_value,
        record_ttl,
    )


@receiver(pre_verify_custom_domain, dispatch_uid="pre_verify_custom_domain")
def handle_pre_verify_custom_domain(sender, **kwargs):
    """Handle pre_verify_custom_domain signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_verify_custom_domain()"
    hosted_zone_id = kwargs.get("hosted_zone_id")
    task_id = kwargs.get("task_id")
    logger.info("%s hosted_zone_id: %s, task_id: %s", prefix, hosted_zone_id, task_id)


@receiver(post_verify_custom_domain, dispatch_uid="post_verify_custom_domain")
def handle_post_verify_custom_domain(sender, **kwargs):
    """Handle post_verify_custom_domain signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_verify_custom_domain()"
    hosted_zone_id = kwargs.get("hosted_zone_id")
    task_id = kwargs.get("task_id")
    logger.info("%s hosted_zone_id: %s, task_id: %s", prefix, hosted_zone_id, task_id)


@receiver(pre_verify_domain, dispatch_uid="pre_verify_domain")
def handle_pre_verify_domain(sender, **kwargs):
    """Handle pre_verify_domain signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_verify_domain()"
    domain_name = kwargs.get("domain_name")
    record_type = kwargs.get("record_type")
    task_id = kwargs.get("task_id")
    logger.info("%s domain_name: %s, record_type: %s, task_id: %s", prefix, domain_name, record_type, task_id)


@receiver(post_verify_domain, dispatch_uid="post_verify_domain")
def handle_post_verify_domain(sender, **kwargs):
    """Handle post_verify_domain signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_verify_domain()"
    domain_name = kwargs.get("domain_name")
    record_type = kwargs.get("record_type")
    task_id = kwargs.get("task_id")
    logger.info("%s domain_name: %s, record_type: %s, task_id: %s", prefix, domain_name, record_type, task_id)


@receiver(pre_destroy_domain_A_record, dispatch_uid="pre_destroy_domain_A_record")
def handle_pre_destroy_domain_A_record(sender, **kwargs):
    """Handle pre_destroy_domain_A_record signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_destroy_domain_A_record()"
    hostname = kwargs.get("hostname")
    api_host_domain = kwargs.get("api_host_domain")
    task_id = kwargs.get("task_id")
    logger.info("%s hostname: %s, api_host_domain: %s, task_id: %s", prefix, hostname, api_host_domain, task_id)


@receiver(post_destroy_domain_A_record, dispatch_uid="post_destroy_domain_A_record")
def handle_post_destroy_domain_A_record(sender, **kwargs):
    """Handle post_destroy_domain_A_record signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_destroy_domain_A_record()"
    hostname = kwargs.get("hostname")
    api_host_domain = kwargs.get("api_host_domain")
    task_id = kwargs.get("task_id")
    logger.info("%s hostname: %s, api_host_domain: %s, task_id: %s", prefix, hostname, api_host_domain, task_id)


@receiver(pre_deploy_default_api, dispatch_uid="pre_deploy_default_api")
def handle_pre_deploy_default_api(sender, **kwargs):
    """Handle pre_deploy_default_api signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_deploy_default_api()"
    llmclient_id = kwargs.get("llmclient_id")
    with_domain_verification = kwargs.get("with_domain_verification")
    task_id = kwargs.get("task_id")
    logger.info(
        "%s llmclient_id: %s, with_domain_verification: %s, task_id: %s",
        prefix,
        llmclient_id,
        with_domain_verification,
        task_id,
    )


@receiver(post_deploy_default_api, dispatch_uid="post_deploy_default_api")
def handle_post_deploy_default_api(sender, **kwargs):
    """Handle post_deploy_default_api signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_deploy_default_api()"
    llmclient_id = kwargs.get("llmclient_id")
    with_domain_verification = kwargs.get("with_domain_verification")
    task_id = kwargs.get("task_id")
    logger.info(
        "%s llmclient_id: %s, with_domain_verification: %s, task_id: %s",
        prefix,
        llmclient_id,
        with_domain_verification,
        task_id,
    )


@receiver(pre_undeploy_default_api, dispatch_uid="pre_undeploy_default_api")
def handle_pre_undeploy_default_api(sender, **kwargs):
    """Handle pre_undeploy_default_api signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_undeploy_default_api()"
    llmclient_id = kwargs.get("llmclient_id")
    task_id = kwargs.get("task_id")
    logger.info("%s llmclient_id: %s, task_id: %s", prefix, llmclient_id, task_id)


@receiver(post_undeploy_default_api, dispatch_uid="post_undeploy_default_api")
def handle_post_undeploy_default_api(sender, **kwargs):
    """Handle post_undeploy_default_api signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_undeploy_default_api()"
    llmclient_id = kwargs.get("llmclient_id")
    task_id = kwargs.get("task_id")
    logger.info("%s llmclient_id: %s, task_id: %s", prefix, llmclient_id, task_id)


@receiver(pre_delete_default_api, dispatch_uid="pre_delete_default_api")
def handle_pre_delete_default_api(sender, **kwargs):
    """Handle pre_delete_default_api signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_delete_default_api()"
    url = kwargs.get("url")
    account_number = kwargs.get("account_number")
    name = kwargs.get("name")
    task_id = kwargs.get("task_id")
    logger.info("%s url: %s, account_number: %s, name: %s, task_id: %s", prefix, url, account_number, name, task_id)


@receiver(post_delete_default_api, dispatch_uid="post_delete_default_api")
def handle_post_delete_default_api(sender, **kwargs):
    """Handle post_delete_default_api signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_delete_default_api()"
    url = kwargs.get("url")
    account_number = kwargs.get("account_number")
    name = kwargs.get("name")
    task_id = kwargs.get("task_id")
    logger.info("%s url: %s, account_number: %s, name: %s, task_id: %s", prefix, url, account_number, name, task_id)


@receiver(pre_deploy_custom_api, dispatch_uid="pre_deploy_custom_api")
def handle_pre_deploy_custom_api(sender, **kwargs):
    """Handle pre_deploy_custom_api signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.pre_deploy_custom_api()"
    llmclient_id = kwargs.get("llmclient_id")
    task_id = kwargs.get("task_id")
    logger.info("%s llmclient_id: %s, task_id: %s", prefix, llmclient_id, task_id)


@receiver(post_deploy_custom_api, dispatch_uid="post_deploy_custom_api")
def handle_post_deploy_custom_api(sender, **kwargs):
    """Handle post_deploy_custom_api signal."""
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.post_deploy_custom_api()"
    llmclient_id = kwargs.get("llmclient_id")
    task_id = kwargs.get("task_id")
    logger.info("%s llmclient_id: %s, task_id: %s", prefix, llmclient_id, task_id)


@receiver(broker_ready, dispatch_uid="broker_ready")
def handle_broker_ready(sender, broker: AbstractBroker, **kwargs):
    """Handle broker ready signal."""
    logger.debug(
        "%s %s %s for %s is ready.",
        f"{logging.SmarterFormattedText.text(module_prefix)}.broker_ready()",
        broker.kind,
        str(broker),
        broker.name,
    )


connect_listview_cache(LLMCLIENT_LISTVIEW_CACHE_KIND, *LLMCLIENT_LISTVIEW_CACHE_MODELS)
connect_listview_cache(CUSTOM_DOMAIN_LISTVIEW_CACHE_KIND, *CUSTOM_DOMAIN_LISTVIEW_CACHE_MODELS)
