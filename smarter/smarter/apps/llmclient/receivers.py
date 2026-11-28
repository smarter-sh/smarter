"""Django Signal Receivers for llmclient."""

# pylint: disable=W0613,C0115
from typing import Optional

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from smarter.apps.llmtool.models import PluginMeta
from smarter.apps.llmtool.signals import plugin_deleting
from smarter.apps.prompt.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.conf import smarter_settings
from smarter.common.utils import mask_identifier
from smarter.lib import json, logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.validators import SmarterValidator
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
    LLMClientVectorsearches,
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

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)

module_prefix = __name__


@receiver(plugin_deleting, dispatch_uid=module_prefix + ".plugin_deleting")
def handle_plugin_deleting(sender, plugin, plugin_meta: PluginMeta, **kwargs):
    """
    Log that a plugin is being deleted.

    :param sender: The signal's sender.
    :param plugin: The plugin being deleted.
    :param plugin_meta: The plugin's metadata, whose name is logged.
    :param kwargs: Other signal arguments (unused).
    """
    logger.info(
        "%s is being deleted. Pruning its usage records.",
        plugin_meta.name,
    )


@receiver(llmclient_deploy_failed, dispatch_uid="llmclient_deploy_failed")
def handle_llmclient_deploy_failed(sender, **kwargs):
    """
    Log that an LLMClient could not be deployed, and why.

    :param sender: The signal's sender, the ``deploy_default_api`` task.
    :param kwargs: The signal's arguments: ``llmclient_id``, ``name`` (when the LLMClient was found),
        ``reason`` and ``task_id``.
    """
    name = kwargs.get("name") or kwargs.get("llmclient_id")
    logger.error("cannot deploy llmclient %s: %s. task_id: %s", name, kwargs.get("reason"), kwargs.get("task_id"))


@receiver(post_save, sender=LLMClient)
def llmclient_saved(sender, instance: LLMClient, created: bool, **kwargs):
    """
    Invalidate the LLMClient's cached host lookups, and log its creation or update.

    At DEBUG level, also logs the serialized LLMClient.

    :param sender: The model class, ``LLMClient``.
    :param instance: The saved LLMClient.
    :param created: True if the LLMClient was created, False if it was updated.
    :param kwargs: Other signal arguments (unused).
    """

    # its hosts may have changed, e.g. when it is renamed.
    invalidate_cached_llmclient_by_hosts(instance)
    logger.info("%s %s", "created" if created else "updated", instance.url)
    # the serialized LLMClient, with its tools, costs several queries, so only when it will be logged.
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", logging.SmarterFormattedText.json(LLMClientSerializer(instance).data))


@receiver(pre_delete, sender=LLMClient)
def llmclient_deleted(sender, instance: LLMClient, **kwargs):
    """
    Invalidate the LLMClient's cached host lookups, and queue the deletion of its default API.

    The ``delete_default_api`` Celery task is queued when the transaction commits, so a rolled-back
    deletion deletes no resources.

    :param sender: The model class, ``LLMClient``.
    :param instance: The LLMClient being deleted.
    :param kwargs: Other signal arguments (unused).
    """
    llmclient: LLMClient = instance
    logger.info("%s", instance.url)
    invalidate_cached_llmclient_by_hosts(llmclient)
    # the task is passed the account number, read now, because the llmclient may be deleted
    # with its account, which then no longer exists when the task runs. It is queued when the
    # deletion is committed, so that a deletion that is rolled back deletes no resources.
    # the task destroys the A record of the default host, which in local Docker differs from the
    # host of the default url.
    api_url = SmarterValidator.urlify(llmclient.default_host, environment=smarter_settings.environment)
    kwargs = {
        "name": llmclient.name,
        "account_number": llmclient.user_profile.account.account_number,  # type: ignore[union-attr]
        "api_url": api_url,
    }
    transaction.on_commit(lambda: delete_default_api.delay(**kwargs))


def llmclient_tools_changed(sender, instance, **kwargs):
    """
    Invalidate an LLMClient's cached tool counts when one of its plugins, extensions or MCPClients is added or removed.

    See :func:`smarter.apps.llmclient.models.utils.get_cached_llmclient_tool_counts`.
    """
    invalidate_cached_llmclient_tool_counts(getattr(instance, "llmclient_id", None))


for _tool_link in (LLMClientPlugin, LLMClientExtensions, LLMClientMCPClients, LLMClientVectorsearches):
    post_save.connect(
        llmclient_tools_changed, sender=_tool_link, dispatch_uid=f"{module_prefix}.{_tool_link.__name__}.post_save"
    )
    post_delete.connect(
        llmclient_tools_changed, sender=_tool_link, dispatch_uid=f"{module_prefix}.{_tool_link.__name__}.post_delete"
    )


@receiver(pre_delete, sender=LLMClientPlugin)
def llmclient_plugin_deleted(sender, instance: LLMClientPlugin, **kwargs):
    """
    Log the deletion of an LLMClientPlugin.

    :param sender: The model class, ``LLMClientPlugin``.
    :param instance: The LLMClientPlugin being deleted.
    :param kwargs: Other signal arguments (unused).
    """
    logger.info("deleting plugin %s for llmclient %s", instance.plugin_meta, instance.llmclient)


@receiver(post_save, sender=LLMClientCustomDomain)
def llmclient_custom_domain_saved(sender, instance: LLMClientCustomDomain, created: bool, **kwargs):
    """
    Log the creation or update of an LLMClientCustomDomain, with its domain name.

    :param sender: The model class, ``LLMClientCustomDomain``.
    :param instance: The saved LLMClientCustomDomain.
    :param created: True if the row was created, False if it was updated.
    :param kwargs: Other signal arguments (unused).
    """
    if created:
        logger.info("created %s", instance.domain_name)
    else:
        logger.info("updated %s", instance.domain_name)


@receiver(post_save, sender=LLMClientCustomDomainDNS)
def llmclient_custom_domain_dns_saved(sender, instance: LLMClientCustomDomainDNS, created: bool, **kwargs):
    """
    Log the creation or update of an LLMClientCustomDomainDNS, with its custom domain's name.

    :param sender: The model class, ``LLMClientCustomDomainDNS``.
    :param instance: The saved LLMClientCustomDomainDNS.
    :param created: True if the row was created, False if it was updated.
    :param kwargs: Other signal arguments (unused).
    """
    if created:
        logger.info("created %s", instance.custom_domain.domain_name)
    else:
        logger.info("updated %s", instance.custom_domain.domain_name)


@receiver(post_save, sender=LLMClientAPIKey)
def llmclient_api_key_saved(sender, instance: LLMClientAPIKey, created: bool, **kwargs):
    """
    Log the creation or update of an LLMClientAPIKey, with its API key.

    :param sender: The model class, ``LLMClientAPIKey``.
    :param instance: The saved LLMClientAPIKey.
    :param created: True if the row was created, False if it was updated.
    :param kwargs: Other signal arguments (unused).
    """
    if created:
        logger.info("created %s", instance.api_key)
    else:
        logger.info("updated %s", instance.api_key)


@receiver(post_save, sender=LLMClientPlugin)
def llmclient_plugin_saved(sender, instance: LLMClientPlugin, created: bool, **kwargs):
    """
    Log the creation or update of an LLMClientPlugin, with its plugin's name.

    :param sender: The model class, ``LLMClientPlugin``.
    :param instance: The saved LLMClientPlugin.
    :param created: True if the row was created, False if it was updated.
    :param kwargs: Other signal arguments (unused).
    """
    if created:
        logger.info("created %s", instance.plugin_meta.name)
    else:
        logger.info("updated %s", instance.plugin_meta.name)


@receiver(post_save, sender=LLMClientExtensions)
def llmclient_extensions_saved(sender, instance: LLMClientExtensions, created: bool, **kwargs):
    """
    Log the creation or update of an LLMClientExtensions, with its extension's slug.

    :param sender: The model class, ``LLMClientExtensions``.
    :param instance: The saved LLMClientExtensions.
    :param created: True if the row was created, False if it was updated.
    :param kwargs: Other signal arguments (unused).
    """
    if created:
        logger.info("created %s", instance.extension.slug)
    else:
        logger.info("updated %s", instance.extension.slug)


@receiver(post_save, sender=LLMClientRequests)
def llmclient_requests_saved(sender, instance: LLMClientRequests, created: bool, **kwargs):
    """
    Log the creation or update of an LLMClientRequests, with its masked session key.

    :param sender: The model class, ``LLMClientRequests``.
    :param instance: The saved LLMClientRequests.
    :param created: True if the row was created, False if it was updated.
    :param kwargs: Other signal arguments (unused).
    """
    if created:
        logger.info("created session %s", mask_identifier(instance.session_key))
    else:
        logger.info("updated session %s", mask_identifier(instance.session_key))


###############################################################################
# Custom Signal handlers for LLMClient deployment and DNS verification status changes
###############################################################################


@receiver(llmclient_deploy_status_changed, dispatch_uid="llmclient_deploy_status_changed")
def handle_llmclient_deploy_status_changed(sender, **kwargs):
    """Handle llmclient_deploy_status_changed signal."""

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info(
        "%s: %s",
        llmclient.url if llmclient else "No llmclient instance provided",
        llmclient.dns_verification_status if llmclient else "N/A",
    )


@receiver(llmclient_undeploy, dispatch_uid="llmclient_undeploy")
def handle_llmclient_undeploy(sender, llmclient: Optional[LLMClient] = None, **kwargs):
    """
    Queue the ``undeploy_default_api`` Celery task for the LLMClient.

    :param sender: The signal's sender.
    :param llmclient: The LLMClient to undeploy. If None, only a log message is written.
    :param kwargs: Other signal arguments (unused).
    """
    if not llmclient:
        logger.warning("no llmclient instance provided. Nothing to undeploy.")
        return
    logger.info("undeploying llmclient %s", llmclient)
    undeploy_default_api.delay(llmclient_id=llmclient.id)  # type: ignore[union-attr]


@receiver(llmclient_deploy, dispatch_uid="llmclient_deploy")
def handle_llmclient_deploy(sender, **kwargs):
    """
    Queue the ``deploy_default_api`` Celery task for the LLMClient.

    :param sender: The signal's sender.
    :param kwargs: The signal's arguments: ``llmclient``, the LLMClient to deploy.
    """
    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    if not llmclient:
        logger.warning("no llmclient instance provided. Nothing to deploy.")
        return
    logger.info("deploying llmclient %s", llmclient.hostname)
    deploy_default_api.delay(llmclient_id=llmclient.id)  # type: ignore[union-attr]


@receiver(llmclient_deployed, dispatch_uid="llmclient_deployed")
def handle_llmclient_deployed(sender, **kwargs):
    """
    Log that an LLMClient was deployed, and deploy it on its custom host too, if it has one.

    :param sender: The signal's sender, the ``deploy_default_api`` task.
    :param kwargs: The signal's arguments: ``llmclient``, the deployed LLMClient, and ``task_id``.
    """
    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    if not llmclient:
        logger.warning("no llmclient instance provided.")
        return
    logger.info(
        "LLMClient %s has been deployed to %s task_id: %s",
        llmclient.name,
        llmclient.default_host,
        kwargs.get("task_id"),
    )
    # an llmclient with a verified custom domain is also served on its custom host.
    if llmclient.custom_host:
        logger.info("deploying llmclient %s on %s", llmclient.name, llmclient.custom_host)
        deploy_custom_api.delay(llmclient_id=llmclient.id)  # type: ignore[union-attr]


@receiver(llmclient_dns_verification_status_changed, dispatch_uid="llmclient_dns_verification_status_changed")
def handle_llmclient_dns_verification_status_changed(sender, **kwargs):
    """Handle llmclient_dns_verification_status_changed signal."""

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info(
        "%s: %s",
        llmclient.hostname if llmclient else "No llmclient instance provided",
        llmclient.dns_verification_status if llmclient else "N/A",
    )


@receiver(llmclient_dns_verification_initiated, dispatch_uid="llmclient_dns_verification_initiated")
def handle_llmclient_dns_verification_initiated(sender, **kwargs):
    """Handle llmclient_dns_verification_initiated signal."""

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info("%s", llmclient.hostname if llmclient else "No llmclient instance provided")


@receiver(llmclient_dns_verified, dispatch_uid="llmclient_dns_verified")
def handle_llmclient_dns_verified(sender, **kwargs):
    """
    Log that a domain resolved to the records it should.

    :param sender: The signal's sender, the ``verify_domain`` task.
    :param kwargs: The signal's arguments: ``domain_name``, ``record_type``, ``addresses`` and ``task_id``.
    """
    logger.info(
        "resolved domain %s to %s records %s task_id: %s",
        kwargs.get("domain_name"),
        kwargs.get("record_type"),
        kwargs.get("addresses"),
        kwargs.get("task_id"),
    )


@receiver(llmclient_dns_failed, dispatch_uid="llmclient_dns_failed")
def handle_llmclient_dns_failed(sender, **kwargs):
    """
    Log that a domain could not be verified, and why.

    :param sender: The signal's sender, e.g. the ``verify_domain`` task.
    :param kwargs: The signal's arguments: ``domain_name``, ``reason`` and ``task_id``.
    """
    logger.warning(
        "unable to verify domain %s: %s. task_id: %s",
        kwargs.get("domain_name"),
        kwargs.get("reason"),
        kwargs.get("task_id"),
    )


@receiver(llmclient_called, dispatch_uid="llmclient_called")
def handle_llmclient_called(sender, **kwargs):
    """
    Log a call to an LLMClient, and queue the ``create_llmclient_request`` Celery task that records it.

    The signal is sent before the view checks the request's method, so a request without a body,
    e.g. a ``GET`` to a route that only accepts ``POST``, arrives here too. That is the client's
    mistake, which the view answers itself (e.g. with a 405): it is logged at DEBUG, and not
    recorded. A missing LLMClient is a programming error, and is logged at ERROR.

    :param sender: The signal's sender.
    :param kwargs: The signal's arguments: ``llmclient``, the LLMClient that was called, and
        ``data``, the request's body. The others are unused.
    """

    llmclient: Optional[LLMClient] = kwargs.get("llmclient")
    logger.info("%s", llmclient.hostname if llmclient else "No llmclient instance provided")

    request_data = kwargs.get("data")
    try:
        if not llmclient:
            logger.error("No llmclient instance provided.")
        elif not request_data:
            logger.debug("%s received a request without a body. Nothing to record.", llmclient.hostname)
        else:
            create_llmclient_request.delay(llmclient.id, request_data)
    except json.JSONDecodeError:
        logger.warning(
            "received an empty or invalid request body from %s",
            llmclient.hostname if llmclient else "No llmclient instance provided",
        )
        request_data = {
            "JSONDecodeError": "received an empty or invalid request body",
        }


###############################################################################
# custom task receivers
###############################################################################


@receiver(pre_create_llmclient_request, dispatch_uid="pre_create_llmclient_request")
def handle_pre_create_llmclient_request(sender, **kwargs):
    """
    Log the size of a chat request that is about to be recorded.

    The request holds the user's prompt, which is personal data, so only its number of messages
    and its masked session key are logged.

    :param sender: The signal's sender, the ``create_llmclient_request`` task.
    :param kwargs: The signal's arguments: ``llmclient_id``, ``request_data`` and ``task_id``.
    """
    request_data = kwargs.get("request_data")
    request_data = json.loads(request_data) if isinstance(request_data, str) else request_data
    messages = None
    session_key = None
    if isinstance(request_data, dict):
        messages = request_data.get("messages")
        session_key = request_data.get(SMARTER_CHAT_SESSION_KEY_NAME)
    logger.debug(
        "llmclient %s task_id: %s received %s message(s) for session %s",
        kwargs.get("llmclient_id"),
        kwargs.get("task_id"),
        len(messages or []),
        mask_identifier(session_key),
    )


@receiver(post_create_llmclient_request, dispatch_uid="post_create_llmclient_request")
def handle_post_create_llmclient_request(sender, **kwargs):
    """Handle post_create_llmclient_request signal."""
    llmclient_id = kwargs.get("llmclient_id")
    request_data = kwargs.get("request_data")
    request_data = json.loads(request_data) if isinstance(request_data, str) else request_data
    session_key = request_data.get(SMARTER_CHAT_SESSION_KEY_NAME) if isinstance(request_data, dict) else None
    logger.debug(
        "llmclient_id: %s, session_key: %s",
        llmclient_id,
        mask_identifier(session_key),
    )


@receiver(pre_register_custom_domain, dispatch_uid="pre_register_custom_domain")
def handle_pre_register_custom_domain(sender, **kwargs):
    """Handle pre_register_custom_domain signal."""
    account_id = kwargs.get("account_id")
    domain_name = kwargs.get("domain_name")
    logger.info("account_id: %s, domain_name: %s", account_id, domain_name)


@receiver(post_register_custom_domain, dispatch_uid="post_register_custom_domain")
def handle_post_register_custom_domain(sender, **kwargs):
    """
    Log the outcome of a custom domain's registration.

    :param sender: The signal's sender, the ``register_custom_domain`` task.
    :param kwargs: The signal's arguments: ``account_id``, ``domain_name``, ``outcome`` and ``task_id``.
    """
    logger.info(
        "custom domain %s of account %s: %s. task_id: %s",
        kwargs.get("domain_name"),
        kwargs.get("account_id"),
        kwargs.get("outcome", "registered"),
        kwargs.get("task_id"),
    )


@receiver(pre_create_custom_domain_dns_record, dispatch_uid="pre_create_custom_domain_dns_record")
def handle_pre_create_custom_domain_dns_record(sender, **kwargs):
    """Log the DNS record that is about to be created for a custom domain."""
    logger.info(
        "creating DNS record %s %s, value %s, ttl %s, for LLMClientCustomDomain %s task_id: %s",
        kwargs.get("record_type"),
        kwargs.get("record_name"),
        kwargs.get("record_value"),
        kwargs.get("record_ttl"),
        kwargs.get("llmclient_custom_domain_id"),
        kwargs.get("task_id"),
    )


@receiver(post_create_custom_domain_dns_record, dispatch_uid="post_create_custom_domain_dns_record")
def handle_post_create_custom_domain_dns_record(sender, **kwargs):
    """Handle post_create_custom_domain_dns_record signal."""
    llmclient_custom_domain_id = kwargs.get("llmclient_custom_domain_id")
    record_name = kwargs.get("record_name")
    record_type = kwargs.get("record_type")
    record_value = kwargs.get("record_value")
    record_ttl = kwargs.get("record_ttl")
    logger.info(
        "llmclient_custom_domain_id: %s, record_name: %s, record_type: %s, record_value: %s, record_ttl: %s",
        llmclient_custom_domain_id,
        record_name,
        record_type,
        record_value,
        record_ttl,
    )


@receiver(pre_verify_custom_domain, dispatch_uid="pre_verify_custom_domain")
def handle_pre_verify_custom_domain(sender, **kwargs):
    """Log that a custom domain's verification started."""
    logger.info(
        "verifying %s, DNS zone %s task_id: %s",
        kwargs.get("domain_name"),
        kwargs.get("hosted_zone_id"),
        kwargs.get("task_id"),
    )


@receiver(post_verify_custom_domain, dispatch_uid="post_verify_custom_domain")
def handle_post_verify_custom_domain(sender, **kwargs):
    """
    Log whether a custom domain was verified, and if not, what blocks it.

    :param sender: The signal's sender, the ``verify_custom_domain`` task.
    :param kwargs: The signal's arguments: ``domain_name``, ``hosted_zone_id``, ``verified``,
        ``blocker`` and ``task_id``.
    """
    domain_name = kwargs.get("domain_name")
    task_id = kwargs.get("task_id")
    if kwargs.get("verified"):
        logger.info("%s is verified: its certificate is issued. task_id %s", domain_name, task_id)
    else:
        logger.error(
            "domain verification failed for domain %s: %s task_id: %s", domain_name, kwargs.get("blocker"), task_id
        )


@receiver(pre_verify_domain, dispatch_uid="pre_verify_domain")
def handle_pre_verify_domain(sender, **kwargs):
    """Log that a domain's verification started."""
    logger.info(
        "verifying domain %s, %s record, task_id: %s",
        kwargs.get("domain_name"),
        kwargs.get("record_type"),
        kwargs.get("task_id"),
    )


@receiver(post_verify_domain, dispatch_uid="post_verify_domain")
def handle_post_verify_domain(sender, **kwargs):
    """
    Log whether a domain was verified.

    :param sender: The signal's sender, the ``verify_domain`` task.
    :param kwargs: The signal's arguments: ``domain_name``, ``record_type``, ``verified``, ``attempts``
        (when it gave up) and ``task_id``.
    """
    domain_name = kwargs.get("domain_name")
    task_id = kwargs.get("task_id")
    verified = kwargs.get("verified")
    if verified is False:
        attempts = kwargs.get("attempts")
        if attempts:
            logger.error("unable to verify domain %s after %s attempts task_id: %s", domain_name, attempts, task_id)
        else:
            logger.error("unable to verify domain %s task_id: %s", domain_name, task_id)
        return
    logger.info("verified domain %s, %s record, task_id: %s", domain_name, kwargs.get("record_type"), task_id)


@receiver(pre_destroy_domain_A_record, dispatch_uid="pre_destroy_domain_A_record")
def handle_pre_destroy_domain_A_record(sender, **kwargs):
    """Handle pre_destroy_domain_A_record signal."""
    hostname = kwargs.get("hostname")
    api_host_domain = kwargs.get("api_host_domain")
    task_id = kwargs.get("task_id")
    logger.info("hostname: %s, api_host_domain: %s, task_id: %s", hostname, api_host_domain, task_id)


@receiver(post_destroy_domain_A_record, dispatch_uid="post_destroy_domain_A_record")
def handle_post_destroy_domain_A_record(sender, **kwargs):
    """Handle post_destroy_domain_A_record signal."""
    hostname = kwargs.get("hostname")
    api_host_domain = kwargs.get("api_host_domain")
    task_id = kwargs.get("task_id")
    logger.info("hostname: %s, api_host_domain: %s, task_id: %s", hostname, api_host_domain, task_id)


@receiver(pre_deploy_default_api, dispatch_uid="pre_deploy_default_api")
def handle_pre_deploy_default_api(sender, **kwargs):
    """Log that an LLMClient's deployment started."""
    logger.info(
        "deploying llmclient %s, with domain verification: %s task_id: %s",
        kwargs.get("llmclient_id"),
        kwargs.get("with_domain_verification"),
        kwargs.get("task_id"),
    )


@receiver(post_deploy_default_api, dispatch_uid="post_deploy_default_api")
def handle_post_deploy_default_api(sender, **kwargs):
    """
    Log the outcome of an LLMClient's deployment task.

    :param sender: The signal's sender, the ``deploy_default_api`` task.
    :param kwargs: The signal's arguments: ``llmclient_id``, ``with_domain_verification``, ``outcome``
        and ``task_id``.
    """
    logger.info(
        "llmclient %s: %s. task_id: %s",
        kwargs.get("llmclient_id"),
        kwargs.get("outcome", "the deployment task finished"),
        kwargs.get("task_id"),
    )


@receiver(pre_undeploy_default_api, dispatch_uid="pre_undeploy_default_api")
def handle_pre_undeploy_default_api(sender, **kwargs):
    """Log that an LLMClient's undeployment started."""
    logger.info("undeploying llmclient %s task_id: %s", kwargs.get("llmclient_id"), kwargs.get("task_id"))


@receiver(post_undeploy_default_api, dispatch_uid="post_undeploy_default_api")
def handle_post_undeploy_default_api(sender, **kwargs):
    """
    Log the outcome of an LLMClient's undeployment task.

    :param sender: The signal's sender, the ``undeploy_default_api`` task.
    :param kwargs: The signal's arguments: ``llmclient_id``, ``success`` (False when it failed),
        ``outcome`` and ``task_id``.
    """
    llmclient_id = kwargs.get("llmclient_id")
    outcome = kwargs.get("outcome", "undeployed")
    task_id = kwargs.get("task_id")
    if kwargs.get("success") is False:
        logger.error("cannot undeploy llmclient %s: %s. task_id: %s", llmclient_id, outcome, task_id)
        return
    logger.info("llmclient %s: %s. task_id: %s", llmclient_id, outcome, task_id)


@receiver(pre_delete_default_api, dispatch_uid="pre_delete_default_api")
def handle_pre_delete_default_api(sender, **kwargs):
    """Log that an LLMClient's default api is about to be deleted."""
    logger.info(
        "deleting the default api %s of llmclient %s, account %s task_id: %s",
        kwargs.get("url"),
        kwargs.get("name"),
        kwargs.get("account_number"),
        kwargs.get("task_id"),
    )


@receiver(post_delete_default_api, dispatch_uid="post_delete_default_api")
def handle_post_delete_default_api(sender, **kwargs):
    """Handle post_delete_default_api signal."""
    url = kwargs.get("url")
    account_number = kwargs.get("account_number")
    name = kwargs.get("name")
    task_id = kwargs.get("task_id")
    logger.info("url: %s, account_number: %s, name: %s, task_id: %s", url, account_number, name, task_id)


@receiver(pre_deploy_custom_api, dispatch_uid="pre_deploy_custom_api")
def handle_pre_deploy_custom_api(sender, **kwargs):
    """Log that an LLMClient is about to be deployed on its custom host."""
    logger.info(
        "deploying llmclient %s on %s task_id: %s",
        kwargs.get("name") or kwargs.get("llmclient_id"),
        kwargs.get("custom_host"),
        kwargs.get("task_id"),
    )


@receiver(post_deploy_custom_api, dispatch_uid="post_deploy_custom_api")
def handle_post_deploy_custom_api(sender, **kwargs):
    """Handle post_deploy_custom_api signal."""
    llmclient_id = kwargs.get("llmclient_id")
    task_id = kwargs.get("task_id")
    logger.info("llmclient_id: %s, task_id: %s", llmclient_id, task_id)


@receiver(broker_ready, dispatch_uid="broker_ready")
def handle_broker_ready(sender, broker: AbstractBroker, **kwargs):
    """
    Log, at DEBUG level, that a manifest broker is ready.

    :param sender: The signal's sender.
    :param broker: The broker that is ready.
    :param kwargs: Other signal arguments (unused).
    """
    logger.debug(
        "%s %s for %s is ready.",
        broker.kind,
        str(broker),
        broker.name,
    )


connect_listview_cache(LLMCLIENT_LISTVIEW_CACHE_KIND, *LLMCLIENT_LISTVIEW_CACHE_MODELS)
connect_listview_cache(CUSTOM_DOMAIN_LISTVIEW_CACHE_KIND, *CUSTOM_DOMAIN_LISTVIEW_CACHE_MODELS)
