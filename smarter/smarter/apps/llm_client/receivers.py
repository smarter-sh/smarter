"""Django Signal Receivers for llm_client."""

# pylint: disable=W0613,C0115
from typing import Optional

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.signals import plugin_deleting
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.broker import AbstractBroker

from .models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
    LLMClientFunctions,
    LLMClientPlugin,
    LLMClientRequests,
)
from .serializers import LLMClientSerializer
from .signals import (
    broker_ready,
    llm_client_called,
    llm_client_deploy,
    llm_client_deploy_failed,
    llm_client_deploy_status_changed,
    llm_client_deployed,
    llm_client_dns_failed,
    llm_client_dns_verification_initiated,
    llm_client_dns_verification_status_changed,
    llm_client_dns_verified,
    llm_client_undeploy,
    post_create_custom_domain_dns_record,
    post_create_llm_client_request,
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
    pre_create_llm_client_request,
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
    create_llm_client_request,
    delete_default_api,
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
        logging.formatted_text(f"{module_prefix}.plugin_deleting"),
        plugin_meta.name,
    )


@receiver(llm_client_deploy_failed, dispatch_uid="llm_client_deploy_failed")
def handle_llm_client_deploy_failed(sender, **kwargs):
    """Handle llm_client_deploy_failed signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_deploy_failed()")
    llm_client: Optional[LLMClient] = kwargs.get("llm_client")
    logger.error("%s - %s", prefix, llm_client.hostname if llm_client else "No llm_client instance provided")


@receiver(post_save, sender=LLMClient)
def llm_client_saved(sender, instance: LLMClient, created: bool, **kwargs):
    """Create the default API for the llm_client."""

    prefix = logging.formatted_text(f"{module_prefix}.llm_client_saved()")
    data = logging.formatted_json(LLMClientSerializer(instance).data)
    if created:
        logger.info("%s - created %s, %s", prefix, instance.url, data)
    else:
        logger.info("%s - updated %s, %s", prefix, instance.url, data)


@receiver(pre_delete, sender=LLMClient)
def llm_client_deleted(sender, instance: LLMClient, **kwargs):
    """Delete the default API for the llm_client."""
    llm_client: LLMClient = instance
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_deleted()")
    logger.info("%s - %s", prefix, instance.url)
    delete_default_api.delay(name=llm_client.name, account_id=llm_client.user_profile.account.id, api_url=llm_client.default_url)  # type: ignore[union-attr]


@receiver(pre_delete, sender=LLMClientPlugin)
def llm_client_plugin_deleted(sender, instance: LLMClientPlugin, **kwargs):
    """Log deletion of LLMClientPlugin."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_plugin_deleted()")
    logger.info("%s - deleting plugin %s for llm_client %s", prefix, instance.plugin_meta, instance.llm_client)


@receiver(post_save, sender=LLMClientCustomDomain)
def llm_client_custom_domain_saved(sender, instance: LLMClientCustomDomain, created: bool, **kwargs):
    """Log creation or update of LLMClientCustomDomain."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_custom_domain_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.domain_name)
    else:
        logger.info("%s - updated %s", prefix, instance.domain_name)


@receiver(post_save, sender=LLMClientCustomDomainDNS)
def llm_client_custom_domain_dns_saved(sender, instance: LLMClientCustomDomainDNS, created: bool, **kwargs):
    """Log creation or update of LLMClientCustomDomainDNS."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_custom_domain_dns_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.custom_domain.domain_name)
    else:
        logger.info("%s - updated %s", prefix, instance.custom_domain.domain_name)


@receiver(post_save, sender=LLMClientAPIKey)
def llm_client_api_key_saved(sender, instance: LLMClientAPIKey, created: bool, **kwargs):
    """Log creation or update of LLMClientAPIKey."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_api_key_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.api_key)
    else:
        logger.info("%s - updated %s", prefix, instance.api_key)


@receiver(post_save, sender=LLMClientPlugin)
def llm_client_plugin_saved(sender, instance: LLMClientPlugin, created: bool, **kwargs):
    """Log creation or update of LLMClientPlugin."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_plugin_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.plugin_meta.name)
    else:
        logger.info("%s - updated %s", prefix, instance.plugin_meta.name)


@receiver(post_save, sender=LLMClientFunctions)
def llm_client_functions_saved(sender, instance: LLMClientFunctions, created: bool, **kwargs):
    """Log creation or update of LLMClientFunctions."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_functions_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.name)
    else:
        logger.info("%s - updated %s", prefix, instance.name)


@receiver(post_save, sender=LLMClientRequests)
def llm_client_requests_saved(sender, instance: LLMClientRequests, created: bool, **kwargs):
    """Log creation or update of LLMClientRequests."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_requests_saved()")
    if created:
        logger.info("%s - created %s", prefix, instance.session_key)
    else:
        logger.info("%s - updated %s", prefix, instance.session_key)


###############################################################################
# Custom Signal handlers for LLMClient deployment and DNS verification status changes
###############################################################################


@receiver(llm_client_deploy_status_changed, dispatch_uid="llm_client_deploy_status_changed")
def handle_llm_client_deploy_status_changed(sender, **kwargs):
    """Handle llm_client_deploy_status_changed signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_deploy_status_changed()")

    llm_client: Optional[LLMClient] = kwargs.get("llm_client")
    logger.info(
        "%s - %s: %s",
        prefix,
        llm_client.url if llm_client else "No llm_client instance provided",
        llm_client.dns_verification_status if llm_client else "N/A",
    )


@receiver(llm_client_undeploy, dispatch_uid="llm_client_undeploy")
def handle_llm_client_undeploy(sender, llm_client: Optional[LLMClient] = None, **kwargs):
    """Handle llm_client_undeploy signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_undeploy()")

    logger.info("%s - %s", prefix, llm_client if llm_client else "No llm_client instance provided")
    if llm_client:
        undeploy_default_api.delay(llm_client_id=llm_client.id)  # type: ignore[union-attr]


@receiver(llm_client_deploy, dispatch_uid="llm_client_deploy")
def handle_llm_client_deploy(sender, **kwargs):
    """Handle llm_client_deploy signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_deploy()")

    llm_client: Optional[LLMClient] = kwargs.get("llm_client")
    logger.info(
        "%s signal received - %s", prefix, llm_client.hostname if llm_client else "No llm_client instance provided"
    )
    if llm_client:
        logger.info("%s deploying llm_client - %s", prefix, llm_client.hostname)
        deploy_default_api.delay(llm_client_id=llm_client.id)  # type: ignore[union-attr]


@receiver(llm_client_deployed, dispatch_uid="llm_client_deployed")
def handle_llm_client_deployed(sender, **kwargs):
    """Handle llm_client_deployed signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_deployed()")

    llm_client: Optional[LLMClient] = kwargs.get("llm_client")
    logger.info("%s - %s", prefix, llm_client.hostname if llm_client else "No llm_client instance provided")


@receiver(llm_client_dns_verification_status_changed, dispatch_uid="llm_client_dns_verification_status_changed")
def handle_llm_client_dns_verification_status_changed(sender, **kwargs):
    """Handle llm_client_dns_verification_status_changed signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_dns_verification_status_changed()")

    llm_client: Optional[LLMClient] = kwargs.get("llm_client")
    logger.info(
        "%s - %s: %s",
        prefix,
        llm_client.hostname if llm_client else "No llm_client instance provided",
        llm_client.dns_verification_status if llm_client else "N/A",
    )


@receiver(llm_client_dns_verification_initiated, dispatch_uid="llm_client_dns_verification_initiated")
def handle_llm_client_dns_verification_initiated(sender, **kwargs):
    """Handle llm_client_dns_verification_initiated signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_dns_verification_initiated()")

    llm_client: Optional[LLMClient] = kwargs.get("llm_client")
    logger.info("%s - %s", prefix, llm_client.hostname if llm_client else "No llm_client instance provided")


@receiver(llm_client_dns_verified, dispatch_uid="llm_client_dns_verified")
def handle_llm_client_dns_verified(sender, **kwargs):
    """Handle llm_client_dns_verified signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_dns_verified()")

    llm_client: Optional[LLMClient] = kwargs.get("llm_client")
    logger.info("%s - %s", prefix, llm_client.hostname if llm_client else "No llm_client instance provided")


@receiver(llm_client_dns_failed, dispatch_uid="llm_client_dns_failed")
def handle_llm_client_dns_failed(sender, **kwargs):
    """Handle llm_client_dns_failed signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_dns_failed()")

    llm_client: Optional[LLMClient] = kwargs.get("llm_client")
    logger.info("%s - %s", prefix, llm_client.hostname if llm_client else "No llm_client instance provided")


@receiver(llm_client_called, dispatch_uid="llm_client_called")
def handle_llm_client_called(sender, **kwargs):
    """Handle llm_client_called signal."""
    prefix = logging.formatted_text(f"{module_prefix}.llm_client_called()")

    llm_client: Optional[LLMClient] = kwargs.get("llm_client")
    logger.info("%s - %s", prefix, llm_client.hostname if llm_client else "No llm_client instance provided")

    request_data = kwargs.get("data")
    try:
        if llm_client and request_data:
            create_llm_client_request.delay(llm_client.id, request_data)
        else:
            logger.error(
                "%s - Missing llm_client instance or request data. LLMClient: %s, Data: %s",
                prefix,
                llm_client.hostname if llm_client else "No llm_client instance provided",
                "Present" if request_data else "No data",
            )
    except json.JSONDecodeError:
        logger.warning(
            "%s received an empty or invalid request body from %s",
            prefix,
            llm_client.hostname if llm_client else "No llm_client instance provided",
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
    prefix = logging.formatted_text(f"{module_prefix}.pre_verify_certificate()")
    certificate_arn = kwargs.get("certificate_arn")
    logger.info("%s - certificate_arn: %s", prefix, certificate_arn)


@receiver(post_verify_certificate, dispatch_uid="post_verify_certificate")
def handle_post_verify_certificate(sender, **kwargs):
    """Handle post_verify_certificate signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_verify_certificate()")
    certificate_arn = kwargs.get("certificate_arn")
    logger.info("%s - certificate_arn: %s", prefix, certificate_arn)


@receiver(pre_create_llm_client_request, dispatch_uid="pre_create_llm_client_request")
def handle_pre_create_llm_client_request(sender, **kwargs):
    """Handle pre_create_llm_client_request signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_create_llm_client_request()")
    llm_client_id = kwargs.get("llm_client_id")
    request_data = kwargs.get("request_data")
    request_data = json.loads(request_data) if isinstance(request_data, str) else request_data
    logger.info(
        "%s - llm_client_id: %s, request_data: %s",
        prefix,
        llm_client_id,
        logging.formatted_json(request_data) if request_data else "No data",
    )


@receiver(post_create_llm_client_request, dispatch_uid="post_create_llm_client_request")
def handle_post_create_llm_client_request(sender, **kwargs):
    """Handle post_create_llm_client_request signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_create_llm_client_request()")
    llm_client_id = kwargs.get("llm_client_id")
    request_data = kwargs.get("request_data")
    request_data = json.loads(request_data) if isinstance(request_data, str) else request_data
    logger.info(
        "%s - llm_client_id: %s, request_data: %s",
        prefix,
        llm_client_id,
        logging.formatted_json(request_data) if request_data else "No data",
    )


@receiver(pre_register_custom_domain, dispatch_uid="pre_register_custom_domain")
def handle_pre_register_custom_domain(sender, **kwargs):
    """Handle pre_register_custom_domain signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_register_custom_domain()")
    account_id = kwargs.get("account_id")
    domain_name = kwargs.get("domain_name")
    logger.info("%s - account_id: %s, domain_name: %s", prefix, account_id, domain_name)


@receiver(post_register_custom_domain, dispatch_uid="post_register_custom_domain")
def handle_post_register_custom_domain(sender, **kwargs):
    """Handle post_register_custom_domain signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_register_custom_domain()")
    account_id = kwargs.get("account_id")
    domain_name = kwargs.get("domain_name")
    logger.info("%s - account_id: %s, domain_name: %s", prefix, account_id, domain_name)


@receiver(pre_create_custom_domain_dns_record, dispatch_uid="pre_create_custom_domain_dns_record")
def handle_pre_create_custom_domain_dns_record(sender, **kwargs):
    """Handle pre_create_custom_domain_dns_record signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_create_custom_domain_dns_record()")
    llm_client_custom_domain_id = kwargs.get("llm_client_custom_domain_id")
    record_name = kwargs.get("record_name")
    record_type = kwargs.get("record_type")
    record_value = kwargs.get("record_value")
    record_ttl = kwargs.get("record_ttl")
    logger.info(
        "%s - llm_client_custom_domain_id: %s, record_name: %s, record_type: %s, record_value: %s, record_ttl: %s",
        prefix,
        llm_client_custom_domain_id,
        record_name,
        record_type,
        record_value,
        record_ttl,
    )


@receiver(post_create_custom_domain_dns_record, dispatch_uid="post_create_custom_domain_dns_record")
def handle_post_create_custom_domain_dns_record(sender, **kwargs):
    """Handle post_create_custom_domain_dns_record signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_create_custom_domain_dns_record()")
    llm_client_custom_domain_id = kwargs.get("llm_client_custom_domain_id")
    record_name = kwargs.get("record_name")
    record_type = kwargs.get("record_type")
    record_value = kwargs.get("record_value")
    record_ttl = kwargs.get("record_ttl")
    logger.info(
        "%s - llm_client_custom_domain_id: %s, record_name: %s, record_type: %s, record_value: %s, record_ttl: %s",
        prefix,
        llm_client_custom_domain_id,
        record_name,
        record_type,
        record_value,
        record_ttl,
    )


@receiver(pre_verify_custom_domain, dispatch_uid="pre_verify_custom_domain")
def handle_pre_verify_custom_domain(sender, **kwargs):
    """Handle pre_verify_custom_domain signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_verify_custom_domain()")
    hosted_zone_id = kwargs.get("hosted_zone_id")
    task_id = kwargs.get("task_id")
    logger.info("%s - hosted_zone_id: %s, task_id: %s", prefix, hosted_zone_id, task_id)


@receiver(post_verify_custom_domain, dispatch_uid="post_verify_custom_domain")
def handle_post_verify_custom_domain(sender, **kwargs):
    """Handle post_verify_custom_domain signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_verify_custom_domain()")
    hosted_zone_id = kwargs.get("hosted_zone_id")
    task_id = kwargs.get("task_id")
    logger.info("%s - hosted_zone_id: %s, task_id: %s", prefix, hosted_zone_id, task_id)


@receiver(pre_verify_domain, dispatch_uid="pre_verify_domain")
def handle_pre_verify_domain(sender, **kwargs):
    """Handle pre_verify_domain signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_verify_domain()")
    domain_name = kwargs.get("domain_name")
    record_type = kwargs.get("record_type")
    task_id = kwargs.get("task_id")
    logger.info("%s - domain_name: %s, record_type: %s, task_id: %s", prefix, domain_name, record_type, task_id)


@receiver(post_verify_domain, dispatch_uid="post_verify_domain")
def handle_post_verify_domain(sender, **kwargs):
    """Handle post_verify_domain signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_verify_domain()")
    domain_name = kwargs.get("domain_name")
    record_type = kwargs.get("record_type")
    task_id = kwargs.get("task_id")
    logger.info("%s - domain_name: %s, record_type: %s, task_id: %s", prefix, domain_name, record_type, task_id)


@receiver(pre_destroy_domain_A_record, dispatch_uid="pre_destroy_domain_A_record")
def handle_pre_destroy_domain_A_record(sender, **kwargs):
    """Handle pre_destroy_domain_A_record signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_destroy_domain_A_record()")
    hostname = kwargs.get("hostname")
    api_host_domain = kwargs.get("api_host_domain")
    task_id = kwargs.get("task_id")
    logger.info("%s - hostname: %s, api_host_domain: %s, task_id: %s", prefix, hostname, api_host_domain, task_id)


@receiver(post_destroy_domain_A_record, dispatch_uid="post_destroy_domain_A_record")
def handle_post_destroy_domain_A_record(sender, **kwargs):
    """Handle post_destroy_domain_A_record signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_destroy_domain_A_record()")
    hostname = kwargs.get("hostname")
    api_host_domain = kwargs.get("api_host_domain")
    task_id = kwargs.get("task_id")
    logger.info("%s - hostname: %s, api_host_domain: %s, task_id: %s", prefix, hostname, api_host_domain, task_id)


@receiver(pre_deploy_default_api, dispatch_uid="pre_deploy_default_api")
def handle_pre_deploy_default_api(sender, **kwargs):
    """Handle pre_deploy_default_api signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_deploy_default_api()")
    llm_client_id = kwargs.get("llm_client_id")
    with_domain_verification = kwargs.get("with_domain_verification")
    task_id = kwargs.get("task_id")
    logger.info(
        "%s - llm_client_id: %s, with_domain_verification: %s, task_id: %s",
        prefix,
        llm_client_id,
        with_domain_verification,
        task_id,
    )


@receiver(post_deploy_default_api, dispatch_uid="post_deploy_default_api")
def handle_post_deploy_default_api(sender, **kwargs):
    """Handle post_deploy_default_api signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_deploy_default_api()")
    llm_client_id = kwargs.get("llm_client_id")
    with_domain_verification = kwargs.get("with_domain_verification")
    task_id = kwargs.get("task_id")
    logger.info(
        "%s - llm_client_id: %s, with_domain_verification: %s, task_id: %s",
        prefix,
        llm_client_id,
        with_domain_verification,
        task_id,
    )


@receiver(pre_undeploy_default_api, dispatch_uid="pre_undeploy_default_api")
def handle_pre_undeploy_default_api(sender, **kwargs):
    """Handle pre_undeploy_default_api signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_undeploy_default_api()")
    llm_client_id = kwargs.get("llm_client_id")
    task_id = kwargs.get("task_id")
    logger.info("%s - llm_client_id: %s, task_id: %s", prefix, llm_client_id, task_id)


@receiver(post_undeploy_default_api, dispatch_uid="post_undeploy_default_api")
def handle_post_undeploy_default_api(sender, **kwargs):
    """Handle post_undeploy_default_api signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_undeploy_default_api()")
    llm_client_id = kwargs.get("llm_client_id")
    task_id = kwargs.get("task_id")
    logger.info("%s - llm_client_id: %s, task_id: %s", prefix, llm_client_id, task_id)


@receiver(pre_delete_default_api, dispatch_uid="pre_delete_default_api")
def handle_pre_delete_default_api(sender, **kwargs):
    """Handle pre_delete_default_api signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_delete_default_api()")
    url = kwargs.get("url")
    account_number = kwargs.get("account_number")
    name = kwargs.get("name")
    task_id = kwargs.get("task_id")
    logger.info("%s - url: %s, account_number: %s, name: %s, task_id: %s", prefix, url, account_number, name, task_id)


@receiver(post_delete_default_api, dispatch_uid="post_delete_default_api")
def handle_post_delete_default_api(sender, **kwargs):
    """Handle post_delete_default_api signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_delete_default_api()")
    url = kwargs.get("url")
    account_number = kwargs.get("account_number")
    name = kwargs.get("name")
    task_id = kwargs.get("task_id")
    logger.info("%s - url: %s, account_number: %s, name: %s, task_id: %s", prefix, url, account_number, name, task_id)


@receiver(pre_deploy_custom_api, dispatch_uid="pre_deploy_custom_api")
def handle_pre_deploy_custom_api(sender, **kwargs):
    """Handle pre_deploy_custom_api signal."""
    prefix = logging.formatted_text(f"{module_prefix}.pre_deploy_custom_api()")
    llm_client_id = kwargs.get("llm_client_id")
    task_id = kwargs.get("task_id")
    logger.info("%s - llm_client_id: %s, task_id: %s", prefix, llm_client_id, task_id)


@receiver(post_deploy_custom_api, dispatch_uid="post_deploy_custom_api")
def handle_post_deploy_custom_api(sender, **kwargs):
    """Handle post_deploy_custom_api signal."""
    prefix = logging.formatted_text(f"{module_prefix}.post_deploy_custom_api()")
    llm_client_id = kwargs.get("llm_client_id")
    task_id = kwargs.get("task_id")
    logger.info("%s - llm_client_id: %s, task_id: %s", prefix, llm_client_id, task_id)


@receiver(broker_ready, dispatch_uid="broker_ready")
def handle_broker_ready(sender, broker: AbstractBroker, **kwargs):
    """Handle broker ready signal."""
    logger.info(
        "%s %s %s for %s is ready.",
        logging.formatted_text(f"{module_prefix}.broker_ready()"),
        broker.kind,
        str(broker),
        broker.name,
    )
