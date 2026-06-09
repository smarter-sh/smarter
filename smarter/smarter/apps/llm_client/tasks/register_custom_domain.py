"""
Celery tasks for registering llm_client custom domains.

This module defines Celery tasks for registering custom domains for llm_clients, including creating AWS Route53 hosted zones, ACM certificates, and DNS records, as well as associating domains with accounts.

Main Tasks
----------

- register_custom_domain(account_id, domain_name):
    Registers a customer's custom domain name in AWS Route53 and associates the hosted zone with the account.

Signals
-------

- pre_register_custom_domain: Sent before custom domain registration begins.
- post_register_custom_domain: Sent after custom domain registration is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Logging
-------

Task execution and domain registration are logged using the smarter logging library, with waffle switches for task and llm_client logging.

Usage
-----

Import this module and call the Celery task as needed to asynchronously register an llm_client custom domain:

    register_custom_domain.delay(account_id, domain_name)

Raises
------

LLMClientCustomDomainExists
    If the domain is already registered to another account.
AWSACMCertificateNotFound
    If the ACM certificate for the domain is not found.
AWSACMVerificationNotFound
    If the ACM certificate for the domain is not verified.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
)
from smarter.apps.llm_client.models import LLMClientCustomDomain
from smarter.apps.llm_client.signals import (
    post_register_custom_domain,
    pre_register_custom_domain,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws.acm import AWSCertificateManager
from smarter.common.helpers.aws.exceptions import (
    AWSACMCertificateNotFound,
    AWSACMVerificationNotFound,
)
from smarter.common.helpers.aws.route53 import AWSRoute53
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .exceptions import LLMClientCustomDomainExists
from .utils import is_taskable
from .verify_certificate import verify_certificate

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
def register_custom_domain(account_id: int, domain_name: str):
    """
    Register a customer's custom domain name in AWS Route53 and associate the Hosted Zone with the account.

    This Celery task performs the following steps:
    1. Sends a pre-register signal for the custom domain.
    2. Checks if the custom domain and certificate already exist and are verified.
    3. Ensures the domain is not registered by another account.
    4. Creates a Hosted Zone for the custom domain if needed.
    5. Associates the Hosted Zone with the account.
    6. Creates or retrieves an ACM certificate for the domain.
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

    Raises
    ------
    LLMClientCustomDomainExists
        If the domain is already registered to another account.
    AWSACMCertificateNotFound
        If the ACM certificate for the domain is not found.
    AWSACMVerificationNotFound
        If the ACM certificate for the domain is not verified.
    Exception
        Any exception raised during the registration process will trigger a retry according to Celery settings.
    """
    if not is_taskable():
        return
    if not isinstance(aws_helper.acm, AWSCertificateManager):
        return False
    if not isinstance(aws_helper.route53, AWSRoute53):
        return False

    task_id = register_custom_domain.request.id
    pre_register_custom_domain.send(
        sender=register_custom_domain, account_id=account_id, domain_name=domain_name, task_id=task_id
    )
    account = Account.objects.get(id=account_id)
    admin = get_cached_admin_user_for_account(account=account)
    admin_user_profile = UserProfile.get_cached_object(user=admin, account=account)  # type: ignore[assignment]
    domain_name = aws_helper.aws.domain_resolver(domain_name)

    logger.info(
        "%s - Account %s %s attempting to register custom domain %s task_id: %s",
        logger_prefix + f".{register_custom_domain.__name__}() task_id: %s",
        account.company_name,
        account.account_number,
        domain_name,
        task_id,
    )
    try:
        LLMClientCustomDomain.objects.get(user_profile__account=account, domain_name=domain_name)
        certificate_arn = aws_helper.acm.get_certificate_arn(domain_name=domain_name)
        if not certificate_arn:
            raise AWSACMCertificateNotFound
        if not aws_helper.acm.certificate_is_verified(certificate_arn=certificate_arn):
            raise AWSACMVerificationNotFound

        # we found the custom domain, and its certificate is verified
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
        return
    except LLMClientCustomDomain.DoesNotExist:
        # the custom domain doesn't exist, so we need to create it
        logger.info(
            "%s - custom domain %s not found for account %s. Proceeding to create it. task_id: %s",
            logger_prefix,
            domain_name,
            account.company_name,
            task_id,
        )
    except AWSACMCertificateNotFound:
        # the certificate was not found, so we need to create it
        logger.info(
            "%s - certificate for domain %s not found. Proceeding to create it. task_id: %s",
            logger_prefix,
            domain_name,
            task_id,
        )
    except AWSACMVerificationNotFound:
        # the certificate has not been verified, so we need to verify it
        logger.info(
            "%s - certificate for domain %s is not verified. Proceeding to verify it. task_id: %s",
            logger_prefix,
            domain_name,
            task_id,
        )

    try:
        # verify that the domain is available to register.
        domain_record = LLMClientCustomDomain.objects.get(domain_name=domain_name)
        err = f"{logger_prefix}.register_custom_domain() - Account {account.company_name} attempted to register {domain_name} but it is already registered to {domain_record.user_profile.account.company_name} task_id: {task_id}"
        logger.error(err)
        raise LLMClientCustomDomainExists(err)
    except LLMClientCustomDomain.DoesNotExist:
        # domain was not previously registered by another account, so we can continue.
        logger.info("%s - domain %s is available to register. task_id: %s", logger_prefix, domain_name, task_id)

    # create a Hosted Zone for the custom domain

    aws_hosted_zone, _ = aws_helper.route53.get_or_create_hosted_zone(domain_name=domain_name)
    host, _ = LLMClientCustomDomain.objects.get_or_create(
        user_profile=admin_user_profile,
        domain_name=domain_name,
    )
    host.aws_hosted_zone_id = aws_hosted_zone["Id"]
    host.save()

    # create a certificate for the custom domain
    certificate_arn = aws_helper.acm.get_or_create_certificate(domain_name=domain_name)

    # create a DNS record for the certificate and wait for it to be verified.
    aws_helper.acm.get_or_create_certificate_dns_record(certificate_arn=certificate_arn)
    verify_certificate.delay(certificate_arn=certificate_arn)
    post_register_custom_domain.send(
        sender=register_custom_domain, account_id=account_id, domain_name=domain_name, task_id=task_id
    )
