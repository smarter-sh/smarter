"""
Celery tasks for deleting llm_client API resources.

This module defines Celery tasks for deleting AWS and Kubernetes resources associated with a llm_client's default API, including Route53 DNS records and ingress resources.

Main Tasks
----------

- delete_default_api(api_url, account_number, name):
    Deletes the default domain Route53 A record and Kubernetes ingress resources (ingress, certificate, secret) for a llm_client API.

Signals
-------

- pre_delete_default_api: Sent before API resource deletion begins.
- post_delete_default_api: Sent after API resource deletion is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and resource deletion are logged using the smarter logging library, with waffle switches for task and llm_client logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously delete llm_client API resources:

    delete_default_api.delay(api_url, account_number, name)

Raises
------

Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from urllib.parse import urlparse

from django.http import HttpRequest

from smarter.apps.account.models import Account
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llm_client.signals import (
    post_delete_default_api,
    pre_delete_default_api,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.k8s_helpers import kubernetes_helper
from smarter.lib import logging
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .destroy_domain_a_record import destroy_domain_A_record
from .utils import is_taskable

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llm_client_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llm_client_tasks_celery_max_retries,
    queue=smarter_settings.llm_client_tasks_celery_task_queue,
)
def delete_default_api(name: str, account_id: int, api_url: str):
    """
    Delete AWS and Kubernetes resources for a customer API.

    Deletes the Kubernetes ingress, certificate, and secret associated with the
    llm_client's named API url, which is of the form "https://{llm_client_name}.{account_number}.api_host_domain/".
    Also deletes the default domain Route53 A record for the llm_client.
    Example api_url: https://stackademy-api.3141-5926-5359.alpha.api.ubc.smarter.sh/

    This Celery task performs the following steps:
    1. Sends a pre-delete signal for the API resources.
    2. Logs the deletion request.
    3. Extracts the domain name from the provided api_url.
    4. Deletes the default domain Route53 A record for the llm_client.
    5. Deletes Kubernetes ingress resources: ingress, certificate, and secret.
    6. Logs the result of the deletion operations.
    7. Sends a post-delete signal for the API resources.

    Parameters
    ----------
    llm_client_id : int
        The ID of the llm_client whose resources are to be deleted.

    Signals
    -------
    pre_delete_default_api : django.dispatch.Signal
        Sent before the deletion of API resources begins.
    post_delete_default_api : django.dispatch.Signal
        Sent after the deletion of API resources is completed.

    Raises
    ------
    Exception
        Any exception raised during the deletion process will trigger a retry according to Celery settings.
    """

    def _get_url_path(api_url):
        """Extracts the path component from a given URL."""
        parsed_url = urlparse(api_url)
        return parsed_url.path

    def _get_domain_name(api_url):
        """Extracts the domain name (netloc) from a given URL."""
        parsed_url = urlparse(api_url)
        domain_name = parsed_url.netloc
        return domain_name

    def _dummy_request_factory(path: str):
        """
        Creates a dummy HttpRequest object with the necessary attributes to be.

        used with SmarterRequestMixin for a given llm_client.
        """
        request = HttpRequest()
        request.user = smarter_cached_objects.smarter_admin
        request.path = path
        request.method = "POST"
        return request

    if not is_taskable():
        return

    account: Account
    try:
        account = Account.get_cached_object(pk=account_id)
    except Account.DoesNotExist as e:
        raise SmarterConfigurationError(
            f"{logger_prefix} - Account with id {account_id} does not exist for llm_client API deletion."
        ) from e

    request_path = _get_url_path(api_url)
    request = _dummy_request_factory(request_path)
    request_mixin = SmarterRequestMixin(request=request)
    if not request_mixin.is_llm_client:
        raise SmarterConfigurationError(
            f"{logger_prefix} - Request path {request.path} is not recognized as a llm_client URL."
        )
    if not request_mixin.is_llm_client_named_url:
        raise SmarterConfigurationError(
            f"{logger_prefix} - Request path {request.path} is not recognized as a llm_client named URL."
        )

    task_id = delete_default_api.request.id
    pre_delete_default_api.send(
        sender=delete_default_api, url=api_url, account_number=account.account_number, name=name, task_id=task_id
    )

    prefix = logger_prefix + f".{delete_default_api.__name__}()"
    logger.info(
        "%s - llm_client %s account: %s name: %s task_id: %s",
        prefix,
        api_url,
        account,
        name,
        task_id,
    )

    hostname = _get_domain_name(api_url)
    destroy_domain_A_record(hostname=hostname, api_host_domain=smarter_settings.environment_api_domain, task_id=task_id)
    ingress_deleted, certificate_deleted, secret_delete = kubernetes_helper.delete_ingress_resources(
        hostname=hostname, namespace=smarter_settings.environment_namespace
    )
    if ingress_deleted and certificate_deleted and secret_delete:
        logger.info(
            "%s - llm_client %s account: %s name: %s all resources successfully deleted task_id: %s",
            prefix,
            api_url,
            account,
            name,
            task_id,
        )
    else:
        logger.error(
            "%s - llm_client %s account: %s name: %s one or more resources were not deleted task_id: %s",
            prefix,
            api_url,
            account,
            name,
            task_id,
        )
    post_delete_default_api.send(
        sender=delete_default_api, url=api_url, account_number=account.account_number, name=name, task_id=task_id
    )
