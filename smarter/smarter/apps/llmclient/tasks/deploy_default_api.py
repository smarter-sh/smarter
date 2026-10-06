"""
Celery tasks for deploying llmclient default API domains.

This module defines Celery tasks for deploying default API domains for llmclients, including the creation and verification of DNS A records, Kubernetes ingress manifests, and certificate issuance.

Main Tasks
----------

- deploy_default_api(llmclient_id, with_domain_verification=True):
    Creates a default domain A record for an llmclient, manages ingress and certificate resources, and optionally verifies the domain.

Signals
-------

- pre_deploy_default_api: Sent before deployment of the default API begins.
- post_deploy_default_api: Sent after deployment of the default API is completed.
- llmclient_deployed: Sent when the llmclient is successfully deployed.
- llmclient_deploy_failed: Sent when deployment fails.
- llmclient_dns_verification_initiated: Sent when DNS verification is initiated.
- llmclient_dns_verified: Sent when DNS verification succeeds.
- llmclient_dns_failed: Sent when DNS verification fails.
- llmclient_dns_verification_status_changed: Sent when DNS verification status changes.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution, resource creation, and deployment status are logged using the smarter logging library, with waffle switches for task and llmclient logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously deploy an llmclient default API domain:

    deploy_default_api.delay(llmclient_id, with_domain_verification=True)

Raises
------

LLMClient.DoesNotExist
    If the LLMClient with the given ID does not exist.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from typing import Optional

from smarter.apps.account.models import AccountContact
from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.signals import (
    llmclient_deploy_failed,
    llmclient_deployed,
    llmclient_dns_failed,
    llmclient_dns_verification_initiated,
    post_deploy_default_api,
    post_verify_domain,
    pre_deploy_default_api,
    pre_verify_domain,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CUSTOMER_SUPPORT_EMAIL
from smarter.common.exceptions import SmarterException
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .utils import apply_ingress_manifest, is_taskable
from .verify_domain import (
    VERIFY_DOMAIN_INTERVAL,
    VERIFY_DOMAIN_MAX_ATTEMPTS,
    DomainCheck,
    check_domain,
    verify_domain,
)

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


# continue_default_api_deployment checks the ingress resources and certificate 10 minutes after
# the ingress is applied, and then every minute, for up to half an hour, without blocking a worker.
STAGE_CERTIFICATE = "certificate"
STAGE_DOMAIN = "domain"
CERTIFICATE_FIRST_CHECK_SECONDS = 600
CERTIFICATE_CHECK_INTERVAL = 60
CERTIFICATE_MAX_ATTEMPTS = 30


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.infrastructure_tasks_celery_task_queue,
)
def deploy_default_api(llmclient_id: int, with_domain_verification: bool = True):
    """
    Create a customer API default domain A record for an llmclient and manage deployment resources.

    This Celery task performs the following steps:

    1. Sends a pre-deploy signal for the llmclient API.
    2. Logs the deployment request.
    3. Retrieves the LLMClient instance by ID.
    4. Creates a DNS A record for the llmclient's default domain.
    5. Optionally creates and applies a Kubernetes ingress manifest for the domain.
    6. Hands off to ``continue_default_api_deployment``, which verifies the ingress resources and the
       certificate, and then the domain, if requested, and activates the llmclient. A certificate and
       a domain take minutes to hours to be ready, so it checks again later rather than waiting, and
       never blocks a worker.
    7. Sends post-deploy and deployment status signals.
    8. Notifies the account owner by email upon successful deployment.

    Parameters
    ----------
    llmclient_id : int
        The primary key of the LLMClient instance for which the default domain A record is being created.
    with_domain_verification : bool, optional
        Whether to perform domain verification after deployment. Default is True.

    Signals
    -------
    pre_deploy_default_api : django.dispatch.Signal
        Sent before deployment of the default API begins.
    post_deploy_default_api : django.dispatch.Signal
        Sent after deployment of the default API is completed.
    llmclient_deployed : django.dispatch.Signal
        Sent when the llmclient is successfully deployed.
    llmclient_deploy_failed : django.dispatch.Signal
        Sent when deployment fails.
    llmclient_dns_verification_initiated : django.dispatch.Signal
        Sent when DNS verification is initiated.
    llmclient_dns_verified : django.dispatch.Signal
        Sent when DNS verification succeeds.
    llmclient_dns_failed : django.dispatch.Signal
        Sent when DNS verification fails.
    llmclient_dns_verification_status_changed : django.dispatch.Signal
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
    logger.info("%s - llmclient %s task_id: %s", fn_name, llmclient_id, task_id)
    llmclient: LLMClient

    pre_deploy_default_api.send(
        sender=deploy_default_api,
        llmclient_id=llmclient_id,
        with_domain_verification=with_domain_verification,
        task_id=task_id,
    )

    try:
        llmclient = LLMClient.objects.get(id=llmclient_id)
        logger.info("%s found llmclient %s for deployment task_id: %s", fn_name, llmclient.name, task_id)
    except LLMClient.DoesNotExist:
        logger.error("%s LLMClient %s not found. Nothing to do, returning. task_id: %s", fn_name, llmclient_id, task_id)

        llmclient_deploy_failed.send(
            sender=deploy_default_api,
            llmclient_id=llmclient_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        return None

    if not infrastructure.dns.ready:
        logger.error(
            "%s the DNS service is not ready. Cannot deploy llmclient %s. task_id: %s",
            fn_name,
            llmclient.name,
            task_id,
        )
        llmclient_deploy_failed.send(
            sender=deploy_default_api, llmclient_id=llmclient_id, with_domain_verification=with_domain_verification
        )
        post_deploy_default_api.send(
            sender=deploy_default_api,
            llmclient_id=llmclient_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        return None

    domain_name = llmclient.default_host
    if smarter_settings.llmclient_tasks_create_dns_record:
        _, created = infrastructure.dns.create_domain_a_record(
            hostname=domain_name, api_host_domain=llmclient.base_api_domain
        )
        if created:
            logger.info(
                "%s created A record for llmclient %s at domain %s task_id: %s",
                fn_name,
                llmclient.name,
                domain_name,
                task_id,
            )
        else:
            logger.info(
                "%s verified the A record for llmclient %s at domain %s. task_id: %s",
                fn_name,
                llmclient.name,
                domain_name,
                task_id,
            )

    if llmclient.deployed and llmclient.dns_verification_status == llmclient.DnsVerificationStatusChoices.VERIFIED:
        logger.info(
            "%s LLMClient %s is already deployed and verified at domain %s. Nothing to do. task_id: %s",
            fn_name,
            llmclient.name,
            domain_name,
            task_id,
        )
        post_deploy_default_api.send(
            sender=deploy_default_api,
            llmclient_id=llmclient_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        return

    # if we're running in Kubernetes then we should create an ingress manifest
    # for the customer API domain so that we can issue a certificate for it.
    if not smarter_settings.llmclient_tasks_create_ingress_manifest:
        logger.info(
            "%s llmclient_tasks_create_ingress_manifest is set to False. Skipping creation of ingress manifest for llmclient %s at domain %s task_id: %s",
            fn_name,
            llmclient.name,
            domain_name,
            task_id,
        )
    else:
        logger.info("%s verifying/creating ingress manifest for %s task_id: %s", fn_name, domain_name, task_id)
        try:
            apply_ingress_manifest(domain_name)
        except SmarterException as e:
            logger.error(
                "%s failed to apply ingress manifest for llmclient %s at domain %s task_id: %s. Error: %s",
                fn_name,
                llmclient.name,
                domain_name,
                task_id,
                str(e),
            )
            llmclient.tls_certificate_issuance_status = llmclient.TlsCertificateIssuanceStatusChoices.FAILED
            llmclient.save(asynchronous=True)
            llmclient_deploy_failed.send(
                sender=deploy_default_api,
                llmclient_id=llmclient_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            post_deploy_default_api.send(
                sender=deploy_default_api,
                llmclient_id=llmclient_id,
                with_domain_verification=with_domain_verification,
                task_id=task_id,
            )
            return

        if llmclient.tls_certificate_issuance_status != llmclient.TlsCertificateIssuanceStatusChoices.ISSUED:
            # move ourselves back to the first step in the process.
            llmclient.tls_certificate_issuance_status = llmclient.TlsCertificateIssuanceStatusChoices.REQUESTED
            llmclient.save(asynchronous=True)
            # the certificate takes minutes to be issued. Rather than wait for it, which would block
            # this worker, continue_default_api_deployment verifies the ingress resources later.
            logger.info(
                "%s checking in %s seconds that the ingress resources were created and that the certificate was issued",
                fn_name,
                CERTIFICATE_FIRST_CHECK_SECONDS,
            )
            continue_default_api_deployment.apply_async(
                kwargs={
                    "llmclient_id": llmclient_id,
                    "with_domain_verification": with_domain_verification,
                    "task_id": task_id,
                    "stage": STAGE_CERTIFICATE,
                },
                countdown=CERTIFICATE_FIRST_CHECK_SECONDS,
            )
            return
        continue_default_api_deployment(
            llmclient_id, with_domain_verification, task_id=task_id, stage=STAGE_CERTIFICATE
        )
        return

    continue_default_api_deployment(llmclient_id, with_domain_verification, task_id=task_id, stage=STAGE_DOMAIN)


def _deployment_failed(llmclient_id: int, with_domain_verification: bool, task_id: Optional[str]) -> None:
    """Send the signals of a deployment that failed."""
    llmclient_deploy_failed.send(
        sender=deploy_default_api,
        llmclient_id=llmclient_id,
        with_domain_verification=with_domain_verification,
        task_id=task_id,
    )
    post_deploy_default_api.send(
        sender=deploy_default_api,
        llmclient_id=llmclient_id,
        with_domain_verification=with_domain_verification,
        task_id=task_id,
    )


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.infrastructure_tasks_celery_task_queue,
)
def continue_default_api_deployment(
    llmclient_id: int,
    with_domain_verification: bool = True,
    task_id: Optional[str] = None,
    stage: str = STAGE_CERTIFICATE,
    attempt: int = 0,
):
    """
    Continue an llmclient's deployment, which deploy_default_api began, without blocking a worker.

    Each run checks once, and if what it checks is not ready yet, it schedules itself to check
    again later, rather than sleeping:

    1. ``certificate``: that the ingress resources were created, and that the certificate was
       issued, every CERTIFICATE_CHECK_INTERVAL seconds, up to CERTIFICATE_MAX_ATTEMPTS times.
    2. ``domain``: if with_domain_verification, that the llmclient's default domain resolves,
       every VERIFY_DOMAIN_INTERVAL seconds, up to VERIFY_DOMAIN_MAX_ATTEMPTS times.

    It then activates the llmclient, and notifies its account's primary contact.

    :param llmclient_id: The id of the LLMClient.
    :param with_domain_verification: Whether to verify the llmclient's default domain.
    :param task_id: The id of the deploy_default_api task, for logging and signals.
    :param stage: ``certificate`` or ``domain``.
    :param attempt: The number of checks of the stage already made.
    """
    fn_name = f"{logger_prefix}.continue_default_api_deployment()"
    if not is_taskable():
        return

    llmclient = LLMClient.objects.filter(id=llmclient_id).first()
    if not llmclient:
        logger.error("%s LLMClient %s not found. Nothing to do, returning. task_id: %s", fn_name, llmclient_id, task_id)
        _deployment_failed(llmclient_id, with_domain_verification, task_id)
        return
    domain_name = llmclient.default_host

    def check_again(next_stage: str, next_attempt: int, countdown: int) -> None:
        continue_default_api_deployment.apply_async(
            kwargs={
                "llmclient_id": llmclient_id,
                "with_domain_verification": with_domain_verification,
                "task_id": task_id,
                "stage": next_stage,
                "attempt": next_attempt,
            },
            countdown=countdown,
        )

    if stage == STAGE_CERTIFICATE:
        # verify that the ingress resources were created:
        ingress_verified, certificate_verified, secret_verified = infrastructure.kubernetes.verify_ingress_resources(
            hostname=domain_name, namespace=smarter_settings.environment_namespace, max_attempts=1
        )
        if not (ingress_verified and secret_verified and certificate_verified):
            if attempt + 1 < CERTIFICATE_MAX_ATTEMPTS:
                logger.info(
                    "%s - llmclient %s ingress resources are not ready. Check %s of %s. task_id: %s",
                    fn_name,
                    domain_name,
                    attempt + 1,
                    CERTIFICATE_MAX_ATTEMPTS,
                    task_id,
                )
                check_again(STAGE_CERTIFICATE, attempt + 1, CERTIFICATE_CHECK_INTERVAL)
                return
            logger.error(
                "%s - llmclient %s %s one or more resources were not created task_id: %s",
                fn_name,
                domain_name,
                llmclient,
                task_id,
            )
            llmclient.tls_certificate_issuance_status = llmclient.TlsCertificateIssuanceStatusChoices.FAILED
            llmclient.save(asynchronous=True)
            _deployment_failed(llmclient_id, with_domain_verification, task_id)
            return

        llmclient.tls_certificate_issuance_status = llmclient.TlsCertificateIssuanceStatusChoices.ISSUED
        llmclient.save(asynchronous=True)
        logger.info(
            "%s - llmclient %s %s all resources successfully created task_id: %s",
            fn_name,
            domain_name,
            llmclient,
            task_id,
        )
        post_deploy_default_api.send(
            sender=deploy_default_api,
            llmclient_id=llmclient_id,
            with_domain_verification=with_domain_verification,
            task_id=task_id,
        )
        llmclient_deployed.send(sender=deploy_default_api, llmclient=llmclient, task_id=task_id)
        stage, attempt = STAGE_DOMAIN, 0

    if with_domain_verification:
        if attempt == 0:
            llmclient.dns_verification_status = llmclient.DnsVerificationStatusChoices.VERIFYING
            llmclient.save(asynchronous=True)
            pre_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type="A", task_id=task_id)
            llmclient_dns_verification_initiated.send(
                sender=verify_domain, domain_name=domain_name, record_type="A", task_id=task_id
            )
        result = check_domain(infrastructure.dns.resolve_domain(domain_name), record_type="A", task_id=task_id)
        if result == DomainCheck.PENDING and attempt + 1 < VERIFY_DOMAIN_MAX_ATTEMPTS:
            check_again(STAGE_DOMAIN, attempt + 1, VERIFY_DOMAIN_INTERVAL)
            return
        if result != DomainCheck.VERIFIED:
            logger.error(
                "%s unable to verify domain %s. LLMClient %s will not be deployed. task_id: %s",
                fn_name,
                domain_name,
                llmclient.name,
                task_id,
            )
            llmclient_dns_failed.send(sender=verify_domain, domain_name=domain_name, record_type="A", task_id=task_id)
            post_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type="A", task_id=task_id)
            llmclient.dns_verification_status = llmclient.DnsVerificationStatusChoices.FAILED
            llmclient.save(asynchronous=True)
            _deployment_failed(llmclient_id, with_domain_verification, task_id)
            return
        # the domain resolves, so the llmclient is activated.
        if not llmclient.deployed:
            llmclient.deployed = True
            llmclient.save(asynchronous=True)
        post_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type="A", task_id=task_id)

    llmclient.dns_verification_status = llmclient.DnsVerificationStatusChoices.VERIFIED
    llmclient.save(asynchronous=True)
    llmclient_deployed.send(sender=deploy_default_api, llmclient=llmclient)
    logger.info("%s LLMClient %s has been deployed to %s task_id: %s", fn_name, llmclient.name, domain_name, task_id)

    # send an email to the account owner to notify them that the llmclient has been deployed
    subject = f"Your Smarter llmclient {llmclient.url} has been deployed"
    body = (
        f"Your llmclient, {llmclient.name}, has been deployed to {llmclient.url}. "
        f"It is now activated and able to respond to prompts.\n\n"
        f"If you also created a custom domain for your llmclient then you'll be separately notified once it has been verified. "
        f"If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."
    )
    AccountContact.send_email_to_primary_contact(
        account=llmclient.user_profile.cached_account, subject=subject, body=body
    )
