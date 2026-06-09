"""
Celery tasks for deploying llm_client default API domains.

This module defines Celery tasks for deploying default API domains for llm_clients, including the creation and verification of Route53 A records, Kubernetes ingress manifests, and certificate issuance.

Main Tasks
----------

- deploy_default_api(llm_client_id, with_domain_verification=True):
    Creates a default domain A record for an llm_client, manages ingress and certificate resources, and optionally verifies the domain.

Signals
-------

- pre_deploy_default_api: Sent before deployment of the default API begins.
- post_deploy_default_api: Sent after deployment of the default API is completed.
- llm_client_deployed: Sent when the llm_client is successfully deployed.
- llm_client_deploy_failed: Sent when deployment fails.
- llm_client_dns_verification_initiated: Sent when DNS verification is initiated.
- llm_client_dns_verified: Sent when DNS verification succeeds.
- llm_client_dns_failed: Sent when DNS verification fails.
- llm_client_dns_verification_status_changed: Sent when DNS verification status changes.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution, resource creation, and deployment status are logged using the smarter logging library, with waffle switches for task and llm_client logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously deploy an llm_client default API domain:

    deploy_default_api.delay(llm_client_id, with_domain_verification=True)

Raises
------

LLMClient.DoesNotExist
    If the LLMClient with the given ID does not exist.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

import os
import time
from string import Template

from smarter.apps.account.models import AccountContact
from smarter.apps.llm_client.models import LLMClient
from smarter.apps.llm_client.signals import (
    llm_client_deploy_failed,
    llm_client_deployed,
    post_deploy_default_api,
    pre_deploy_default_api,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CUSTOMER_SUPPORT_EMAIL
from smarter.common.exceptions import SmarterException
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.common.helpers.k8s_helpers import kubernetes_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .utils import is_taskable
from .verify_domain import verify_domain

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llm_client_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llm_client_tasks_celery_max_retries,
    queue=smarter_settings.llm_client_tasks_celery_task_queue,
)
def deploy_default_api(llm_client_id: int, with_domain_verification: bool = True):
    """
    Create a customer API default domain A record for an llm_client and manage deployment resources.

    This Celery task performs the following steps:
    1. Sends a pre-deploy signal for the llm_client API.
    2. Logs the deployment request.
    3. Retrieves the LLMClient instance by ID.
    4. Creates a Route53 A record for the llm_client's default domain.
    5. Optionally creates and applies a Kubernetes ingress manifest for the domain.
    6. Verifies ingress resources and certificate issuance.
    7. Handles domain verification if requested.
    8. Sends post-deploy and deployment status signals.
    9. Notifies the account owner by email upon successful deployment.

    Parameters
    ----------
    llm_client_id : int
        The primary key of the LLMClient instance for which the default domain A record is being created.
    with_domain_verification : bool, optional
        Whether to perform domain verification after deployment. Default is True.

    Signals
    -------
    pre_deploy_default_api : django.dispatch.Signal
        Sent before deployment of the default API begins.
    post_deploy_default_api : django.dispatch.Signal
        Sent after deployment of the default API is completed.
    llm_client_deployed : django.dispatch.Signal
        Sent when the llm_client is successfully deployed.
    llm_client_deploy_failed : django.dispatch.Signal
        Sent when deployment fails.
    llm_client_dns_verification_initiated : django.dispatch.Signal
        Sent when DNS verification is initiated.
    llm_client_dns_verified : django.dispatch.Signal
        Sent when DNS verification succeeds.
    llm_client_dns_failed : django.dispatch.Signal
        Sent when DNS verification fails.
    llm_client_dns_verification_status_changed : django.dispatch.Signal
        Sent when DNS verification status changes.

    Raises
    ------
    LLMClient.DoesNotExist
        If the LLMClient with the given ID does not exist.
    Exception
        Any exception raised during the deployment process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return

    fn_name = logger_prefix + ".deploy_default_api()"
    task_id = deploy_default_api.request.id
    logger.info("%s - llm_client %s task_id: %s", fn_name, llm_client_id, task_id)
    llm_client: LLMClient

    pre_deploy_default_api.send(
        sender=deploy_default_api,
        llm_client_id=llm_client_id,
        with_domain_verification=with_domain_verification,
        task_id=task_id,
    )

    try:
        llm_client = LLMClient.objects.get(id=llm_client_id)
        logger.info("%s found llm_client %s for deployment task_id: %s", fn_name, llm_client.name, task_id)
    except LLMClient.DoesNotExist:
        logger.error(
            "%s LLMClient %s not found. Nothing to do, returning. task_id: %s", fn_name, llm_client_id, task_id
        )

        llm_client_deploy_failed.send(
            sender=deploy_default_api,
            llm_client_id=llm_client_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        return None

    # to quiet linting errors
    if not aws_helper.route53:
        logger.error(
            "%s AWS Route53 helper is not available. Cannot deploy llm_client %s. task_id: %s",
            fn_name,
            llm_client.name,
            task_id,
        )
        llm_client_deploy_failed.send(
            sender=deploy_default_api, llm_client_id=llm_client_id, with_domain_verification=with_domain_verification
        )
        post_deploy_default_api.send(
            sender=deploy_default_api,
            llm_client_id=llm_client_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        return None

    domain_name = llm_client.default_host
    if smarter_settings.llm_client_tasks_create_dns_record:
        _, created = aws_helper.route53.create_domain_a_record(
            hostname=domain_name, api_host_domain=llm_client.base_api_domain
        )
        if created:
            logger.info(
                "%s created A record for llm_client %s at domain %s task_id: %s",
                fn_name,
                llm_client.name,
                domain_name,
                task_id,
            )
        else:
            logger.info(
                "%s verified the A record for llm_client %s at domain %s. task_id: %s",
                fn_name,
                llm_client.name,
                domain_name,
                task_id,
            )

    if llm_client.deployed and llm_client.dns_verification_status == llm_client.DnsVerificationStatusChoices.VERIFIED:
        logger.info(
            "%s LLMClient %s is already deployed and verified at domain %s. Nothing to do. task_id: %s",
            fn_name,
            llm_client.name,
            domain_name,
            task_id,
        )
        post_deploy_default_api.send(
            sender=deploy_default_api,
            llm_client_id=llm_client_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        return

    # if we're running in Kubernetes then we should create an ingress manifest
    # for the customer API domain so that we can issue a certificate for it.
    if not smarter_settings.llm_client_tasks_create_ingress_manifest:
        logger.info(
            "%s llm_client_tasks_create_ingress_manifest is set to False. Skipping creation of ingress manifest for llm_client %s at domain %s task_id: %s",
            fn_name,
            llm_client.name,
            domain_name,
            task_id,
        )
    else:
        logger.info("%s verifying/creating ingress manifest for %s task_id: %s", fn_name, domain_name, task_id)
        ingress_values = {
            "app_name": smarter_settings.platform_name,
            "cluster_issuer": smarter_settings.environment_api_domain,
            "environment_namespace": smarter_settings.environment_namespace,
            "domain": domain_name,
            "service_name": "smarter",
        }

        # create and apply the ingress manifest
        template_path = os.path.join(HERE, "../k8s/ingress.yaml.tpl")
        with open(template_path, encoding="utf-8") as ingress_template:
            template = Template(ingress_template.read())
            manifest = template.substitute(ingress_values)

        try:
            kubernetes_helper.apply_manifest(manifest)
        except SmarterException as e:
            logger.error(
                "%s failed to apply ingress manifest for llm_client %s at domain %s task_id: %s. Error: %s",
                fn_name,
                llm_client.name,
                domain_name,
                task_id,
                str(e),
            )
            llm_client.tls_certificate_issuance_status = llm_client.TlsCertificateIssuanceStatusChoices.FAILED
            llm_client.save(asynchronous=True)
            llm_client_deploy_failed.send(
                sender=deploy_default_api,
                llm_client_id=llm_client_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            post_deploy_default_api.send(
                sender=deploy_default_api,
                llm_client_id=llm_client_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            return

        if llm_client.tls_certificate_issuance_status != llm_client.TlsCertificateIssuanceStatusChoices.ISSUED:
            # move ourselves back to the first step in the process.
            llm_client.tls_certificate_issuance_status = llm_client.TlsCertificateIssuanceStatusChoices.REQUESTED
            llm_client.save(asynchronous=True)
            wait_time = 600
            logger.info(
                "%s waiting %s seconds for ingress resources to be created and for certificate to be issued",
                fn_name,
                wait_time,
            )
            time.sleep(wait_time)

        # verify that the ingress resources were created:
        ingress_verified, secret_verified, certificate_verified = kubernetes_helper.verify_ingress_resources(
            hostname=domain_name, namespace=smarter_settings.environment_namespace
        )
        if ingress_verified and secret_verified and certificate_verified:
            llm_client.tls_certificate_issuance_status = llm_client.TlsCertificateIssuanceStatusChoices.ISSUED
            llm_client.save(asynchronous=True)
            logger.info(
                "%s - llm_client %s %s all resources successfully created task_id: %s",
                fn_name,
                domain_name,
                llm_client,
                task_id,
            )
        else:
            logger.error(
                "%s - llm_client %s %s one or more resources were not created task_id: %s",
                fn_name,
                domain_name,
                llm_client,
                task_id,
            )
            llm_client.tls_certificate_issuance_status = llm_client.TlsCertificateIssuanceStatusChoices.FAILED
            llm_client.save(asynchronous=True)
            llm_client_deploy_failed.send(
                sender=deploy_default_api,
                llm_client_id=llm_client_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            post_deploy_default_api.send(
                sender=deploy_default_api,
                llm_client_id=llm_client_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            return

        post_deploy_default_api.send(
            sender=deploy_default_api,
            llm_client_id=llm_client_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        llm_client_deployed.send(sender=deploy_default_api, llm_client=llm_client, task_id=task_id)

    if with_domain_verification:
        llm_client.dns_verification_status = llm_client.DnsVerificationStatusChoices.VERIFYING
        llm_client.save(asynchronous=True)
        verified_domain = verify_domain(
            domain_name, record_type="A", llm_client=llm_client, activate_llm_client=True, task_id=task_id
        )
        if not verified_domain:
            logger.error(
                "%s unable to verify domain %s. LLMClient %s will not be deployed. task_id: %s",
                fn_name,
                domain_name,
                llm_client.name,
                task_id,
            )
            llm_client.dns_verification_status = llm_client.DnsVerificationStatusChoices.FAILED
            llm_client.save(asynchronous=True)
            llm_client_deploy_failed.send(
                sender=deploy_default_api,
                llm_client_id=llm_client_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            post_deploy_default_api.send(
                sender=deploy_default_api,
                llm_client_id=llm_client_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            return

    llm_client.dns_verification_status = llm_client.DnsVerificationStatusChoices.VERIFIED
    llm_client.save(asynchronous=True)
    llm_client_deployed.send(sender=deploy_default_api, llm_client=llm_client)
    logger.info("%s LLMClient %s has been deployed to %s task_id: %s", fn_name, llm_client.name, domain_name, task_id)

    # send an email to the account owner to notify them that the llm_client has been deployed
    subject = f"Your Smarter llm_client {llm_client.url} has been deployed"
    body = (
        f"Your llm_client, {llm_client.name}, has been deployed to {llm_client.url}. "
        f"It is now activated and able to respond to prompts.\n\n"
        f"If you also created a custom domain for your llm_client then you'll be separately notified once it has been verified. "
        f"If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."
    )
    AccountContact.send_email_to_primary_contact(
        account=llm_client.user_profile.cached_account, subject=subject, body=body
    )
