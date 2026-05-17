"""
Celery tasks for deploying chatbot default API domains.

This module defines Celery tasks for deploying default API domains for chatbots, including the creation and verification of Route53 A records, Kubernetes ingress manifests, and certificate issuance.

Main Tasks
----------

- deploy_default_api(chatbot_id, with_domain_verification=True):
    Creates a default domain A record for a chatbot, manages ingress and certificate resources, and optionally verifies the domain.

Signals
-------

- pre_deploy_default_api: Sent before deployment of the default API begins.
- post_deploy_default_api: Sent after deployment of the default API is completed.
- chatbot_deployed: Sent when the chatbot is successfully deployed.
- chatbot_deploy_failed: Sent when deployment fails.
- chatbot_dns_verification_initiated: Sent when DNS verification is initiated.
- chatbot_dns_verified: Sent when DNS verification succeeds.
- chatbot_dns_failed: Sent when DNS verification fails.
- chatbot_dns_verification_status_changed: Sent when DNS verification status changes.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution, resource creation, and deployment status are logged using the smarter logging library, with waffle switches for task and chatbot logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously deploy a chatbot default API domain:

    deploy_default_api.delay(chatbot_id, with_domain_verification=True)

Raises
------

ChatBot.DoesNotExist
    If the ChatBot with the given ID does not exist.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

import os
import time
from string import Template

from smarter.apps.account.models import AccountContact
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.signals import (
    chatbot_deploy_failed,
    chatbot_deployed,
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
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.CHATBOT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def deploy_default_api(chatbot_id: int, with_domain_verification: bool = True):
    """
    Create a customer API default domain A record for a chatbot and manage deployment resources.

    This Celery task performs the following steps:
    1. Sends a pre-deploy signal for the chatbot API.
    2. Logs the deployment request.
    3. Retrieves the ChatBot instance by ID.
    4. Creates a Route53 A record for the chatbot's default domain.
    5. Optionally creates and applies a Kubernetes ingress manifest for the domain.
    6. Verifies ingress resources and certificate issuance.
    7. Handles domain verification if requested.
    8. Sends post-deploy and deployment status signals.
    9. Notifies the account owner by email upon successful deployment.

    Parameters
    ----------
    chatbot_id : int
        The primary key of the ChatBot instance for which the default domain A record is being created.
    with_domain_verification : bool, optional
        Whether to perform domain verification after deployment. Default is True.

    Signals
    -------
    pre_deploy_default_api : django.dispatch.Signal
        Sent before deployment of the default API begins.
    post_deploy_default_api : django.dispatch.Signal
        Sent after deployment of the default API is completed.
    chatbot_deployed : django.dispatch.Signal
        Sent when the chatbot is successfully deployed.
    chatbot_deploy_failed : django.dispatch.Signal
        Sent when deployment fails.
    chatbot_dns_verification_initiated : django.dispatch.Signal
        Sent when DNS verification is initiated.
    chatbot_dns_verified : django.dispatch.Signal
        Sent when DNS verification succeeds.
    chatbot_dns_failed : django.dispatch.Signal
        Sent when DNS verification fails.
    chatbot_dns_verification_status_changed : django.dispatch.Signal
        Sent when DNS verification status changes.

    Raises
    ------
    ChatBot.DoesNotExist
        If the ChatBot with the given ID does not exist.
    Exception
        Any exception raised during the deployment process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return

    fn_name = logger_prefix + ".deploy_default_api()"
    task_id = deploy_default_api.request.id
    logger.info("%s - chatbot %s task_id: %s", fn_name, chatbot_id, task_id)
    chatbot: ChatBot

    pre_deploy_default_api.send(
        sender=deploy_default_api,
        chatbot_id=chatbot_id,
        with_domain_verification=with_domain_verification,
        task_id=task_id,
    )

    try:
        chatbot = ChatBot.objects.get(id=chatbot_id)
        logger.info("%s found chatbot %s for deployment task_id: %s", fn_name, chatbot.name, task_id)
    except ChatBot.DoesNotExist:
        logger.error("%s Chatbot %s not found. Nothing to do, returning. task_id: %s", fn_name, chatbot_id, task_id)

        chatbot_deploy_failed.send(
            sender=deploy_default_api,
            chatbot_id=chatbot_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        return None

    # to quiet linting errors
    if not aws_helper.route53:
        logger.error(
            "%s AWS Route53 helper is not available. Cannot deploy chatbot %s. task_id: %s",
            fn_name,
            chatbot.name,
            task_id,
        )
        chatbot_deploy_failed.send(
            sender=deploy_default_api, chatbot_id=chatbot_id, with_domain_verification=with_domain_verification
        )
        post_deploy_default_api.send(
            sender=deploy_default_api,
            chatbot_id=chatbot_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        return None

    domain_name = chatbot.default_host
    if smarter_settings.chatbot_tasks_create_dns_record:
        _, created = aws_helper.route53.create_domain_a_record(
            hostname=domain_name, api_host_domain=chatbot.base_api_domain
        )
        if created:
            logger.info(
                "%s created A record for chatbot %s at domain %s task_id: %s",
                fn_name,
                chatbot.name,
                domain_name,
                task_id,
            )
        else:
            logger.info(
                "%s verified the A record for chatbot %s at domain %s. task_id: %s",
                fn_name,
                chatbot.name,
                domain_name,
                task_id,
            )

    if chatbot.deployed and chatbot.dns_verification_status == chatbot.DnsVerificationStatusChoices.VERIFIED:
        logger.info(
            "%s Chatbot %s is already deployed and verified at domain %s. Nothing to do. task_id: %s",
            fn_name,
            chatbot.name,
            domain_name,
            task_id,
        )
        post_deploy_default_api.send(
            sender=deploy_default_api,
            chatbot_id=chatbot_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        return

    # if we're running in Kubernetes then we should create an ingress manifest
    # for the customer API domain so that we can issue a certificate for it.
    if not smarter_settings.chatbot_tasks_create_ingress_manifest:
        logger.info(
            "%s chatbot_tasks_create_ingress_manifest is set to False. Skipping creation of ingress manifest for chatbot %s at domain %s task_id: %s",
            fn_name,
            chatbot.name,
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
        template_path = os.path.join(HERE, "./k8s/ingress.yaml.tpl")
        with open(template_path, encoding="utf-8") as ingress_template:
            template = Template(ingress_template.read())
            manifest = template.substitute(ingress_values)

        try:
            kubernetes_helper.apply_manifest(manifest)
        except SmarterException as e:
            logger.error(
                "%s failed to apply ingress manifest for chatbot %s at domain %s task_id: %s. Error: %s",
                fn_name,
                chatbot.name,
                domain_name,
                task_id,
                str(e),
            )
            chatbot.tls_certificate_issuance_status = chatbot.TlsCertificateIssuanceStatusChoices.FAILED
            chatbot.save(asynchronous=True)
            chatbot_deploy_failed.send(
                sender=deploy_default_api,
                chatbot_id=chatbot_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            post_deploy_default_api.send(
                sender=deploy_default_api,
                chatbot_id=chatbot_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            return

        if chatbot.tls_certificate_issuance_status != chatbot.TlsCertificateIssuanceStatusChoices.ISSUED:
            # move ourselves back to the first step in the process.
            chatbot.tls_certificate_issuance_status = chatbot.TlsCertificateIssuanceStatusChoices.REQUESTED
            chatbot.save(asynchronous=True)
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
            chatbot.tls_certificate_issuance_status = chatbot.TlsCertificateIssuanceStatusChoices.ISSUED
            chatbot.save(asynchronous=True)
            logger.info(
                "%s - chatbot %s %s all resources successfully created task_id: %s",
                fn_name,
                domain_name,
                chatbot,
                task_id,
            )
        else:
            logger.error(
                "%s - chatbot %s %s one or more resources were not created task_id: %s",
                fn_name,
                domain_name,
                chatbot,
                task_id,
            )
            chatbot.tls_certificate_issuance_status = chatbot.TlsCertificateIssuanceStatusChoices.FAILED
            chatbot.save(asynchronous=True)
            chatbot_deploy_failed.send(
                sender=deploy_default_api,
                chatbot_id=chatbot_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            post_deploy_default_api.send(
                sender=deploy_default_api,
                chatbot_id=chatbot_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            return

        post_deploy_default_api.send(
            sender=deploy_default_api,
            chatbot_id=chatbot_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        chatbot_deployed.send(sender=deploy_default_api, chatbot=chatbot, task_id=task_id)

    if with_domain_verification:
        chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.VERIFYING
        chatbot.save(asynchronous=True)
        verified_domain = verify_domain(
            domain_name, record_type="A", chatbot=chatbot, activate_chatbot=True, task_id=task_id
        )
        if not verified_domain:
            logger.error(
                "%s unable to verify domain %s. Chatbot %s will not be deployed. task_id: %s",
                fn_name,
                domain_name,
                chatbot.name,
                task_id,
            )
            chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.FAILED
            chatbot.save(asynchronous=True)
            chatbot_deploy_failed.send(
                sender=deploy_default_api,
                chatbot_id=chatbot_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            post_deploy_default_api.send(
                sender=deploy_default_api,
                chatbot_id=chatbot_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            return

    chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.VERIFIED
    chatbot.save(asynchronous=True)
    chatbot_deployed.send(sender=deploy_default_api, chatbot=chatbot)
    logger.info("%s Chatbot %s has been deployed to %s task_id: %s", fn_name, chatbot.name, domain_name, task_id)

    # send an email to the account owner to notify them that the chatbot has been deployed
    subject = f"Your Smarter chatbot {chatbot.url} has been deployed"
    body = (
        f"Your chatbot, {chatbot.name}, has been deployed to {chatbot.url}. "
        f"It is now activated and able to respond to prompts.\n\n"
        f"If you also created a custom domain for your chatbot then you'll be separately notified once it has been verified. "
        f"If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."
    )
    AccountContact.send_email_to_primary_contact(
        account=chatbot.user_profile.cached_account, subject=subject, body=body
    )
