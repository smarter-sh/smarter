"""
Celery tasks for deleting chatbot API resources.

This module defines Celery tasks for deleting AWS and Kubernetes resources associated with a chatbot's default API, including Route53 DNS records and ingress resources.

Main Tasks
----------

- delete_default_api(url, account_number, name):
    Deletes the default domain Route53 A record and Kubernetes ingress resources (ingress, certificate, secret) for a chatbot API.

Signals
-------

- pre_delete_default_api: Sent before API resource deletion begins.
- post_delete_default_api: Sent after API resource deletion is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and resource deletion are logged using the smarter logging library, with waffle switches for task and chatbot logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously delete chatbot API resources:

    delete_default_api.delay(url, account_number, name)

Raises
------

Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from urllib.parse import urlparse

from smarter.apps.chatbot.signals import (
    post_delete_default_api,
    pre_delete_default_api,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.k8s_helpers import kubernetes_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .destroy_domain_a_record import destroy_domain_A_record
from .utils import is_taskable

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
def delete_default_api(url: str, account_number: str, name: str):
    """
    Delete AWS and Kubernetes resources for a customer API.

    This Celery task performs the following steps:
    1. Sends a pre-delete signal for the API resources.
    2. Logs the deletion request.
    3. Extracts the domain name from the provided URL.
    4. Deletes the default domain Route53 A record for the chatbot.
    5. Deletes Kubernetes ingress resources: ingress, certificate, and secret.
    6. Logs the result of the deletion operations.
    7. Sends a post-delete signal for the API resources.

    Parameters
    ----------
    url : str
        The URL of the customer API whose resources are to be deleted.
    account_number : str
        The AWS account number associated with the customer API.
    name : str
        The name of the chatbot or API for which resources are being deleted.

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

    task_id = delete_default_api.request.id
    pre_delete_default_api.send(
        sender=delete_default_api, url=url, account_number=account_number, name=name, task_id=task_id
    )

    prefix = logger_prefix + f".{delete_default_api.__name__}()"
    logger.info(
        "%s - chatbot %s account_number: %s name: %s task_id: %s",
        prefix,
        url,
        account_number,
        name,
        task_id,
    )

    def get_domain_name(url):
        parsed_url = urlparse(url)
        domain_name = parsed_url.netloc
        return domain_name

    hostname = get_domain_name(url)
    destroy_domain_A_record(hostname=hostname, api_host_domain=smarter_settings.environment_api_domain, task_id=task_id)
    ingress_deleted, certificate_deleted, secret_delete = kubernetes_helper.delete_ingress_resources(
        hostname=hostname, namespace=smarter_settings.environment_namespace
    )
    if ingress_deleted and certificate_deleted and secret_delete:
        logger.info(
            "%s - chatbot %s account_number: %s name: %s all resources successfully deleted task_id: %s",
            prefix,
            url,
            account_number,
            name,
            task_id,
        )
    else:
        logger.error(
            "%s - chatbot %s account_number: %s name: %s one or more resources were not deleted task_id: %s",
            prefix,
            url,
            account_number,
            name,
            task_id,
        )
    post_delete_default_api.send(
        sender=delete_default_api, url=url, account_number=account_number, name=name, task_id=task_id
    )
