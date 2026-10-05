"""
Celery tasks for deploying an llmclient on its custom domain.

An llmclient whose custom domain is verified is served on its own subdomain of that domain,
its custom host: ``<llmclient>.<custom domain>``, e.g. ``support.llmclients.example.com``.
Deploying it there takes the same two steps as deploying it on its default host:

1. **DNS**: an A record for the custom host, in the custom domain's AWS Route53 hosted zone. It
   is a copy of the A record of the platform's API domain, so it points to the platform.
2. **Ingress**: a Kubernetes ingress for the custom host. cert-manager issues the custom host's
   own TLS certificate for it.

The custom domain itself, i.e. its NS delegation and its ACM certificate, is verified by
:func:`~smarter.apps.llmclient.tasks.verify_custom_domain`, which deploys the llmclient that uses
the domain once the domain is verified.

Main Tasks
----------

- deploy_custom_api(llmclient_id):
    Creates the custom host's A record and ingress, for an llmclient that is deployed and whose
    custom domain is verified. It does nothing otherwise. It is idempotent.

Signals
-------

- pre_deploy_custom_api: Sent before deployment of the custom API begins.
- post_deploy_custom_api: Sent after deployment of the custom API is completed.

Usage
-----

    deploy_custom_api.delay(llmclient_id)

Raises
------

Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from typing import Optional

from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.signals import (
    post_deploy_custom_api,
    pre_deploy_custom_api,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .utils import apply_ingress_manifest, is_taskable

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
def deploy_custom_api(llmclient_id: int) -> Optional[str]:
    """
    Deploy an llmclient on its custom domain: create its custom host's A record and ingress.

    :param llmclient_id: The id of the llmclient.
    :returns: The custom host, e.g. ``support.llmclients.example.com``, or None if the llmclient
        was not deployed on its custom domain, because it does not exist, is not deployed, or its
        custom domain is missing or not verified.
    """
    prefix = logger_prefix + f".{deploy_custom_api.__name__}()"
    task_id = deploy_custom_api.request.id
    if not is_taskable():
        return None
    llmclient = LLMClient.objects.filter(id=llmclient_id).select_related("custom_domain").first()
    if llmclient is None:
        logger.warning("%s LLMClient %s not found. Nothing to do. task_id: %s", prefix, llmclient_id, task_id)
        return None
    custom_domain = llmclient.custom_domain
    # custom_host is None unless the llmclient has a verified custom domain.
    custom_host = llmclient.custom_host
    if not llmclient.deployed or not custom_domain or not custom_host:
        logger.info(
            "%s LLMClient %s is not deployed, or has no verified custom domain. Nothing to do. task_id: %s",
            prefix,
            llmclient.name,
            task_id,
        )
        return None

    pre_deploy_custom_api.send(sender=deploy_custom_api, llmclient_id=llmclient_id)
    logger.info("%s deploying llmclient %s on %s task_id: %s", prefix, llmclient.name, custom_host, task_id)

    if smarter_settings.llmclient_tasks_create_dns_record:
        # the custom host's A record is a copy of the platform API domain's A record, in the
        # custom domain's own hosted zone.
        _, created = aws_helper.route53.create_domain_a_record(  # type: ignore[union-attr]
            hostname=custom_host,
            api_host_domain=llmclient.base_api_domain,
            hosted_zone_id=custom_domain.aws_hosted_zone_id,
        )
        logger.info(
            "%s %s the A record of %s task_id: %s", prefix, "created" if created else "verified", custom_host, task_id
        )
    if smarter_settings.llmclient_tasks_create_ingress_manifest:
        # cert-manager issues the custom host's own TLS certificate for its ingress.
        apply_ingress_manifest(custom_host)
        logger.info("%s applied the ingress of %s task_id: %s", prefix, custom_host, task_id)

    post_deploy_custom_api.send(sender=deploy_custom_api, llmclient_id=llmclient_id, task_id=task_id)
    return custom_host
