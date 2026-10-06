"""
Celery tasks for deleting llmclient API resources.

This module defines Celery tasks for deleting the DNS and Kubernetes resources associated with an llmclient's default API, including its DNS A record and ingress resources.

Main Tasks
----------

- delete_default_api(api_url, account_number, name):
    Deletes the default domain's DNS A record and Kubernetes ingress resources (ingress, certificate, secret) for an llmclient API.

Signals
-------

- pre_delete_default_api: Sent before API resource deletion begins.
- post_delete_default_api: Sent after API resource deletion is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and resource deletion are logged using the smarter logging library, with waffle switches for task and llmclient logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously delete llmclient API resources:

    delete_default_api.delay(name=name, api_url=api_url, account_number=account_number)

Raises
------

Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from typing import Optional
from urllib.parse import urlparse

from smarter.apps.account.models import Account
from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.llmclient.signals import (
    post_delete_default_api,
    pre_delete_default_api,
)
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .destroy_domain_a_record import destroy_domain_A_record
from .utils import is_taskable

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


def _account_number_from_hostname(hostname: str) -> Optional[str]:
    """
    Return the account number of an llmclient's default api hostname.

    The hostname is "{llmclient name}.{account number}.{environment api domain}",
    e.g. example.3141-5926-5359.alpha.api.example.com
    """
    labels = hostname.split(".")
    if len(labels) < 3 or not SmarterValidator.is_valid_account_number(labels[1]):
        return None
    return labels[1]


def _is_default_api_hostname(hostname: str, account_number: Optional[str]) -> bool:
    """Return True if the hostname is the default api hostname of an llmclient of the account."""
    return bool(account_number) and _account_number_from_hostname(hostname) == account_number


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.infrastructure_tasks_celery_task_queue,
)
def delete_default_api(
    name: str,
    api_url: str,
    account_number: Optional[str] = None,
    account_id: Optional[int] = None,
):
    """
    Delete the DNS and Kubernetes resources of a customer API.

    Deletes the Kubernetes ingress, certificate, and secret associated with the
    llmclient's named API url, which is of the form "https://{llmclient_name}.{account_number}.api_host_domain/".
    Also deletes the default domain's DNS A record for the llmclient.
    Example api_url: https://stackademy-api.3141-5926-5359.alpha.api.ubc.smarter.sh/

    This Celery task performs the following steps:
    1. Sends a pre-delete signal for the API resources.
    2. Logs the deletion request.
    3. Extracts the domain name from the provided api_url.
    4. Deletes the default domain's DNS A record for the llmclient.
    5. Deletes Kubernetes ingress resources: ingress, certificate, and secret.
    6. Logs the result of the deletion operations.
    7. Sends a post-delete signal for the API resources.

    Parameters
    ----------
    name : str
        The llmclient's name.
    api_url : str
        The llmclient's default api url, e.g. https://example.3141-5926-5359.alpha.api.example.com/
    account_number : str, optional
        The account number of the llmclient's account. The task is queued when the llmclient
        is deleted, which may be because its account is being deleted, so the account may no
        longer exist when the task runs. The caller passes the account number, which the task
        uses instead of looking the account up.
    account_id : int, optional
        Deprecated: the id of the llmclient's account, which tasks queued by earlier versions pass.
        The account number is looked up from it if the account still exists, and is otherwise
        taken from the api url's hostname.

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

    if not is_taskable():
        return

    hostname = urlparse(api_url).netloc
    if account_number is None and account_id is not None:
        try:
            account_number = Account.get_cached_object(pk=account_id).account_number  # type: ignore[union-attr]
        except Account.DoesNotExist:
            logger.warning(
                "%s - account %s no longer exists. Using the account number of the api url %s.",
                logger_prefix,
                account_id,
                api_url,
            )
    account_number = account_number or _account_number_from_hostname(hostname)
    if not _is_default_api_hostname(hostname, account_number):
        # not retried: a retry can't make the url valid.
        logger.error(
            "%s - %s is not the default api url of an llmclient of account %s. Nothing was deleted.",
            logger_prefix,
            api_url,
            account_number,
        )
        return

    task_id = delete_default_api.request.id
    pre_delete_default_api.send(
        sender=delete_default_api, url=api_url, account_number=account_number, name=name, task_id=task_id
    )

    prefix = logger_prefix + f".{delete_default_api.__name__}()"
    logger.info(
        "%s - llmclient %s account: %s name: %s task_id: %s",
        prefix,
        api_url,
        account_number,
        name,
        task_id,
    )

    destroy_domain_A_record(hostname=hostname, api_host_domain=smarter_settings.environment_api_domain, task_id=task_id)
    ingress_deleted, certificate_deleted, secret_delete = infrastructure.kubernetes.delete_ingress_resources(
        hostname=hostname, namespace=smarter_settings.environment_namespace
    )
    if ingress_deleted and certificate_deleted and secret_delete:
        logger.info(
            "%s - llmclient %s account: %s name: %s all resources successfully deleted task_id: %s",
            prefix,
            api_url,
            account_number,
            name,
            task_id,
        )
    else:
        logger.error(
            "%s - llmclient %s account: %s name: %s one or more resources were not deleted task_id: %s",
            prefix,
            api_url,
            account_number,
            name,
            task_id,
        )
    post_delete_default_api.send(
        sender=delete_default_api, url=api_url, account_number=account_number, name=name, task_id=task_id
    )
