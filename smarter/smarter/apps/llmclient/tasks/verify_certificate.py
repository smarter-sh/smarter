"""
Celery tasks for verifying llmclient TLS certificates.

This module defines Celery tasks for verifying the cloud provider's TLS certificates (e.g. AWS ACM) associated with llmclient custom domains, including signal handling and logging.

Main Tasks
----------

- verify_certificate(certificate_arn):
    Verifies the status of a TLS certificate and logs the result.

Signals
-------

- pre_verify_certificate: Sent before certificate verification begins.
- post_verify_certificate: Sent after certificate verification is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and certificate verification are logged using the smarter logging library, with waffle switches for task and llmclient logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously verify an llmclient TLS certificate:

    verify_certificate.delay(certificate_arn)

Raises
------

Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.llmclient.signals import (
    post_verify_certificate,
    pre_verify_certificate,
)
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .utils import is_taskable

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.infrastructure_tasks_celery_task_queue,
)
def verify_certificate(certificate_arn: str):
    """
    Verify a TLS certificate.

    This Celery task waits for the cloud provider to issue a TLS certificate, sending pre- and post-verification signals and logging the result.

    Parameters
    ----------
    certificate_arn : str
        The cloud provider's id of the certificate, e.g. the ARN of an AWS ACM certificate.

    Signals
    -------
    pre_verify_certificate : django.dispatch.Signal
        Sent before certificate verification begins.
    post_verify_certificate : django.dispatch.Signal
        Sent after certificate verification is completed.

    Returns
    -------
    None

    Raises
    ------
    Exception
        Any exception raised during the verification process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return

    task_id = verify_certificate.request.id

    pre_verify_certificate.send(sender=verify_certificate, certificate_arn=certificate_arn, task_id=task_id)
    prefix = logger_prefix + ".verify_certificate()"
    logger.info("%s - %s task_id: %s", prefix, certificate_arn, task_id)

    verified = infrastructure.certificates.wait_until_issued(certificate_arn)
    if verified:
        logger.info("%s - certificate %s verified. task_id: %s", prefix, certificate_arn, task_id)
    else:
        logger.error("%s - certificate %s verification failed. task_id: %s", prefix, certificate_arn, task_id)
    post_verify_certificate.send(sender=verify_certificate, certificate_arn=certificate_arn, task_id=task_id)
