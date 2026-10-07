"""
Celery tasks for registering llmclient custom domains.

This module defines Celery tasks for registering custom domains for llmclients, including creating DNS zones, TLS certificates, and DNS records in the cloud provider, as well as associating domains with accounts.

Main Tasks
----------

- register_custom_domain(account_id, domain_name):
    Registers a customer's custom domain name in the cloud provider's DNS and associates its zone with the account.

Signals
-------

- pre_register_custom_domain: Sent before custom domain registration begins.
- post_register_custom_domain: Sent after custom domain registration is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and domain registration are logged using the smarter logging library, with waffle switches for task and llmclient logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously register an llmclient custom domain:

    register_custom_domain.delay(account_id, domain_name)

Raises
------

LLMClientCustomDomainExists
    If the domain is already registered to another account.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
)
from smarter.apps.infrastructure.exceptions import (
    CertificateNotFound,
    CertificateNotIssued,
)
from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.llmclient.models import LLMClientCustomDomain
from smarter.apps.llmclient.signals import (
    post_register_custom_domain,
    pre_register_custom_domain,
)
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .exceptions import LLMClientCustomDomainExists
from .utils import is_taskable
from .verify_custom_domain import verify_custom_domain

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
def register_custom_domain(account_id: int, domain_name: str) -> bool:
    """
    Register a customer's custom domain name in the cloud provider's DNS and associate its zone with the account.

    This Celery task performs the following steps:
    1. Sends a pre-register signal for the custom domain.
    2. Checks if the custom domain and certificate already exist and are verified.
    3. Ensures the domain is not registered by another account.
    4. Creates a DNS zone for the custom domain if needed.
    5. Associates the DNS zone with the account.
    6. Creates or retrieves a TLS certificate for the domain.
    7. Creates a DNS record for the certificate and triggers verification.
    8. Sends a post-register signal for the custom domain.

    Parameters
    ----------
    account_id : int
        The primary key of the Account for which the custom domain is being registered.
    domain_name : str
        The custom domain name to register.

    Signals
    -------
    pre_register_custom_domain : django.dispatch.Signal
        Sent before the custom domain registration begins.
    post_register_custom_domain : django.dispatch.Signal
        Sent after the custom domain registration is completed.

    Returns
    -------
    bool
        True if the domain is registered, or already was, and False if the infrastructure
        services are not available, so nothing was done.

    Raises
    ------
    LLMClientCustomDomainExists
        If the domain is already registered to another account.
    Exception
        Any exception raised during the registration process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return False

    task_id = register_custom_domain.request.id
    pre_register_custom_domain.send(
        sender=register_custom_domain, account_id=account_id, domain_name=domain_name, task_id=task_id
    )
    account = Account.objects.get(id=account_id)
    admin = get_cached_admin_user_for_account(account=account)
    admin_user_profile = UserProfile.get_cached_object(user=admin, account=account)  # type: ignore[assignment]
    domain_name = infrastructure.dns.resolve_domain(domain_name)

    logger.info(
        "%s - Account %s %s attempting to register custom domain %s task_id: %s",
        logger_prefix + f".{register_custom_domain.__name__}() task_id: %s",
        account.company_name,
        account.account_number,
        domain_name,
        task_id,
    )
    try:
        existing = LLMClientCustomDomain.objects.get(user_profile__account=account, domain_name=domain_name)
        certificate_id = infrastructure.certificates.get_certificate_id(domain_name)
        if not certificate_id:
            raise CertificateNotFound(f"{domain_name} has no certificate.")
        if not infrastructure.certificates.is_issued(certificate_id):
            raise CertificateNotIssued(f"The certificate of {domain_name} is not issued.")

        # we found the custom domain, and its certificate is issued. verify it, unless it is verified.
        if existing.aws_hosted_zone_id and not existing.is_verified:
            existing.set_verification_status(
                LLMClientCustomDomain.VerificationStatusChoices.VERIFYING, "Verification has started."
            )
            verify_custom_domain.delay(hosted_zone_id=existing.aws_hosted_zone_id)
        logger.info(
            "%s - custom domain %s already exists for account %s and certificate is verified. Nothing to do. task_id: %s",
            logger_prefix,
            domain_name,
            account.company_name,
            task_id,
        )
        post_register_custom_domain.send(
            sender=register_custom_domain, account_id=account_id, domain_name=domain_name, task_id=task_id
        )
        return True
    except LLMClientCustomDomain.DoesNotExist:
        # the custom domain doesn't exist, so we need to create it
        logger.info(
            "%s - custom domain %s not found for account %s. Proceeding to create it. task_id: %s",
            logger_prefix,
            domain_name,
            account.company_name,
            task_id,
        )
    except CertificateNotFound:
        # the certificate was not found, so we need to create it
        logger.info(
            "%s - certificate for domain %s not found. Proceeding to create it. task_id: %s",
            logger_prefix,
            domain_name,
            task_id,
        )
    except CertificateNotIssued:
        # the certificate has not been verified, so we need to verify it
        logger.info(
            "%s - certificate for domain %s is not verified. Proceeding to verify it. task_id: %s",
            logger_prefix,
            domain_name,
            task_id,
        )

    # verify that no other account has registered the domain. The account's own CustomDomain,
    # e.g. from smarter apply, is the one that this task registers.
    domain_record = (
        LLMClientCustomDomain.objects.filter(domain_name=domain_name).exclude(user_profile__account=account).first()
    )
    if domain_record is not None:
        err = f"{logger_prefix}.register_custom_domain() - Account {account.company_name} attempted to register {domain_name} but it is already registered to {domain_record.user_profile.account.company_name} task_id: {task_id}"
        logger.error(err)
        raise LLMClientCustomDomainExists(err)
    logger.info("%s - domain %s is available to register. task_id: %s", logger_prefix, domain_name, task_id)

    # create a DNS zone for the custom domain
    zone, _ = infrastructure.dns.get_or_create_zone(domain_name)
    # the account's CustomDomain resource, e.g. from smarter apply, whoever in the account owns it.
    host = LLMClientCustomDomain.objects.filter(user_profile__account=account, domain_name=domain_name).first()
    if host is None:
        host = LLMClientCustomDomain.objects.create(user_profile=admin_user_profile, domain_name=domain_name)
    host.aws_hosted_zone_id = zone.id
    host.save()

    # create a certificate for the custom domain
    certificate_id, _ = infrastructure.certificates.get_or_create_certificate(domain_name)

    # create the DNS records that validate the certificate. The provider can only read them once the
    # customer has delegated the domain's NS records to the DNS zone, which may take a day,
    # so rather than wait here, verify_custom_domain checks the NS records, the certificate and
    # https, and checks again later until they work.
    infrastructure.certificates.create_validation_records(certificate_id)
    host.set_verification_status(LLMClientCustomDomain.VerificationStatusChoices.VERIFYING, "Verification has started.")
    verify_custom_domain.delay(hosted_zone_id=host.aws_hosted_zone_id)
    post_register_custom_domain.send(
        sender=register_custom_domain, account_id=account_id, domain_name=domain_name, task_id=task_id
    )
    return True
