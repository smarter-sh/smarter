"""
Celery tasks for verifying llmclient custom domains.

A custom domain is verified when it is delegated to Smarter and its TLS certificate is issued,
which takes two steps, checked in order:

1. **NS delegation**: the domain's public NS records include one of the name servers of its
   AWS Route53 hosted zone, i.e. the customer has delegated the domain to Smarter.
2. **TLS certificate**: the domain's AWS ACM certificate is ``ISSUED``. ACM validates the
   certificate with a DNS record in the hosted zone, so it can only be issued after step 1.
   A certificate is requested if the domain has none.

https itself is served by each LLMClient that uses the domain, on its own subdomain,
``<llmclient>.<domain>``, with its own Kubernetes-managed certificate. The LLMClient's
deployment handles that, not the custom domain's verification.

Main Tasks
----------

- verify_custom_domain(hosted_zone_id, sleep_interval=None, max_attempts=None):
    Checks the steps once. If a step is not complete, it records why in the custom domain's
    ``verification_message``, and schedules itself to check again, until ``max_attempts``.

The custom domain's ``verification_status`` is Verifying while it is checked, Verified, with
``verified_at``, once its certificate is issued, and Failed if it is still not verified after the last attempt.
A domain that is already Verified stays Verified while it is re-verified, until it fails.

Signals
-------

- pre_verify_custom_domain: Sent before custom domain verification begins.
- post_verify_custom_domain: Sent after custom domain verification is completed.

Configuration
-------------

Celery task behavior (retries, backoff, queue) is controlled by `smarter_settings`.

Usage
-----

    verify_custom_domain.delay(hosted_zone_id, sleep_interval, max_attempts)

Raises
------

LLMClientTaskError
    If the hosted zone data is not in the expected format.
Exception
    Any exception during task execution will trigger a retry according to Celery settings.
"""

from typing import Optional

import dns.resolver

from smarter.apps.account.models import Account, AccountContact
from smarter.apps.llmclient.models import LLMClient, LLMClientCustomDomain
from smarter.apps.llmclient.signals import (
    post_verify_custom_domain,
    pre_verify_custom_domain,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CUSTOMER_SUPPORT_EMAIL
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .exceptions import LLMClientTaskError
from .utils import is_taskable

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.LLM_CLIENT_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)

CERTIFICATE_ISSUED = "ISSUED"

Status = LLMClientCustomDomain.VerificationStatusChoices


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.infrastructure_tasks_celery_task_queue,
)
def verify_custom_domain(
    hosted_zone_id: Optional[str] = None,
    sleep_interval: Optional[int] = None,
    max_attempts: Optional[int] = None,
    attempt: int = 0,
    task_id: Optional[str] = None,
    custom_domain_id: Optional[int] = None,
) -> Optional[bool]:
    """
    Verify that the custom domain of an AWS Route53 hosted zone is delegated to Smarter, and that its.

    TLS certificate is issued.

    Each run checks the verification steps once, in order. If a step is not complete, the task
    records why, and schedules itself to check again in sleep_interval seconds, up to max_attempts
    times, rather than sleeping, so that it never blocks a Celery worker while DNS changes.

    Parameters
    ----------
    hosted_zone_id : str, optional
        The ID of the AWS Route53 hosted zone of the custom domain.
    custom_domain_id : int, optional
        The id of the custom domain, in place of its hosted zone. A custom domain that has no
        hosted zone, because it has not been registered with ``smarter deploy``, fails at once.
    sleep_interval : int, optional
        The interval in seconds between verification attempts. Default is 1800 (30 minutes).
    max_attempts : int, optional
        The maximum number of verification attempts. Default is calculated for 24 hours.
    attempt : int, optional
        The number of checks already made. The task passes it when it schedules itself again.
    task_id : str, optional
        The id of the first run, for logging and signals.

    Returns
    -------
    bool or None
        True if the domain is verified, False if it is not after max_attempts checks, and None
        if it will be checked again.
    """
    fn_name = logger_prefix + ".verify_custom_domain()"
    task_id = task_id or verify_custom_domain.request.id
    if not hosted_zone_id:
        custom_domain = LLMClientCustomDomain.objects.filter(pk=custom_domain_id).first()
        if custom_domain is None:
            logger.error("%s custom domain %s not found. task_id: %s", fn_name, custom_domain_id, task_id)
            return False
        if not custom_domain.aws_hosted_zone_id:
            # nothing can be verified, and nothing will change, until the domain is registered.
            message = (
                f"{custom_domain.domain_name} has no AWS Route53 hosted zone, because it is not registered. "
                "Run smarter deploy to register it."
            )
            logger.warning("%s %s task_id: %s", fn_name, message, task_id)
            custom_domain.set_verification_status(Status.FAILED, message)
            return False
        hosted_zone_id = custom_domain.aws_hosted_zone_id
    if not is_taskable():
        return False
    if not aws_helper.route53:
        return False
    hours = 24
    sleep_interval = sleep_interval or 1800
    max_attempts = max_attempts or int(hours * (3600 / sleep_interval))

    hosted_zone = aws_helper.route53.get_hosted_zone_by_id(hosted_zone_id=hosted_zone_id)
    if not isinstance(hosted_zone, dict):
        raise LLMClientTaskError(f"expected a dict but received {type(hosted_zone)}")
    domain_name = hosted_zone["HostedZone"]["Name"].rstrip(".")
    custom_domain = LLMClientCustomDomain.objects.filter(aws_hosted_zone_id=hosted_zone_id).first()

    if attempt == 0:
        logger.info(
            "%s - verifying %s, AWS Route53 Hosted Zone %s task_id: %s", fn_name, domain_name, hosted_zone_id, task_id
        )
        pre_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)
        if custom_domain and not custom_domain.is_verified:
            custom_domain.set_verification_status(Status.VERIFYING, "Verification has started.")
    logger.info(
        "%s - %s %s Attempt: %s of %s task_id: %s",
        fn_name,
        hosted_zone_id,
        domain_name,
        attempt + 1,
        max_attempts,
        task_id,
    )

    blocker = _verification_blocker(hosted_zone_id, domain_name, task_id)
    if blocker is None:
        logger.info("%s %s is verified: its certificate is issued. task_id %s", fn_name, domain_name, task_id)
        if custom_domain:
            custom_domain.set_verification_status(Status.VERIFIED)
            _deploy_llmclient_on(custom_domain)
            _notify(
                custom_domain,
                subject=f"Domain Verification for {domain_name} Successful",
                body=(
                    f"Your domain {domain_name} has been verified: its DNS is delegated to Smarter, and its "
                    "TLS certificate is issued.\n\n"
                    "Your custom domain is now active and ready to use with your LLMClients.\n"
                    f"If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."
                ),
            )
        else:
            logger.info("%s domain %s is not a LLMClient custom domain.", fn_name, domain_name)
        post_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)
        return True

    logger.info("%s %s is not verified yet: %s task_id %s", fn_name, domain_name, blocker, task_id)
    if attempt + 1 < max_attempts:
        if custom_domain and not custom_domain.is_verified:
            custom_domain.set_verification_status(Status.VERIFYING, blocker)
        # check again later, without blocking this worker while DNS changes.
        verify_custom_domain.apply_async(
            kwargs={
                "hosted_zone_id": hosted_zone_id,
                "sleep_interval": sleep_interval,
                "max_attempts": max_attempts,
                "attempt": attempt + 1,
                "task_id": task_id,
            },
            countdown=sleep_interval,
        )
        return None

    logger.error(
        "%s - Domain verification failed for domain %s: %s task_id: %s", fn_name, domain_name, blocker, task_id
    )
    if custom_domain:
        custom_domain.set_verification_status(Status.FAILED, blocker)
        _notify(
            custom_domain,
            subject=f"Domain Verification Failure for {domain_name}",
            body=(
                f"We were unable to verify your domain {domain_name}: {blocker}\n\n"
                f"We made {max_attempts} attempts over a period of {hours} hours to verify the domain.\n"
                f"If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."
            ),
        )
    post_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)
    return False


def _verification_blocker(hosted_zone_id: str, domain_name: str, task_id: Optional[str]) -> Optional[str]:
    """
    Check the verification steps in order.

    :returns: Why the first incomplete step is not complete, or None if the domain is verified.
    """
    if not _ns_records_verified(hosted_zone_id, domain_name, task_id):
        ns_records = [record["Value"] for record in aws_helper.route53.get_ns_records(hosted_zone_id=hosted_zone_id)]  # type: ignore[union-attr]
        return (
            f"The NS records of {domain_name} are not delegated to Smarter yet. "
            f"Add these NS records to your root domain's DNS settings: {', '.join(ns_records)}"
        )
    certificate_status = _certificate_status(domain_name)
    if certificate_status != CERTIFICATE_ISSUED:
        return f"The TLS certificate of {domain_name} is not issued yet. Its status is {certificate_status}."
    return None


def _ns_records_verified(hosted_zone_id: str, domain_name: str, task_id: Optional[str]) -> bool:
    """Check once whether the domain's public NS records include one of its Route53 hosted zone's name servers."""
    fn_name = logger_prefix + "._ns_records_verified()"
    try:
        dns_ns_records = {rdata.to_text() for rdata in dns.resolver.query(domain_name, "NS")}
    except dns.resolver.NXDOMAIN:
        logger.warning("%s domain %s does not exist.", fn_name, domain_name)
        return False
    except dns.resolver.Timeout:
        logger.warning("%s timeout exceeded while querying the domain %s.", fn_name, domain_name)
        return False
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("%s unexpected error while querying domain %s: %s", fn_name, domain_name, str(e))
        return False

    aws_ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=hosted_zone_id)  # type: ignore[union-attr]
    for i, record in enumerate(aws_ns_records, start=1):
        logger.info(
            "%s checking AWS NS record %s (%s of %s) against DNS NS records %s task_id: %s",
            fn_name,
            record["Value"],
            i,
            len(aws_ns_records),
            dns_ns_records,
            task_id,
        )
        if record["Value"] in dns_ns_records:
            return True
    return False


def _certificate_status(domain_name: str) -> str:
    """
    Return the status of the domain's AWS ACM certificate, e.g. PENDING_VALIDATION or ISSUED.

    If the domain has no certificate, one is requested, with its DNS validation record.
    """
    acm = aws_helper.acm
    if acm is None:
        return "unavailable: AWS ACM is not available"
    certificate_arn = acm.get_certificate_arn(domain_name=domain_name)
    if not certificate_arn:
        certificate_arn = acm.get_or_create_certificate(domain_name=domain_name)
        acm.get_or_create_certificate_dns_record(certificate_arn=certificate_arn)
    return acm.certificate_status(certificate_arn=certificate_arn)


def _deploy_llmclient_on(custom_domain: LLMClientCustomDomain) -> None:
    """Deploy the llmclient that uses the custom domain, if it is deployed, on its custom host."""
    # pylint: disable=import-outside-toplevel
    from .deploy_custom_api import deploy_custom_api

    llmclient = LLMClient.objects.filter(custom_domain=custom_domain, deployed=True).first()
    if llmclient:
        deploy_custom_api.delay(llmclient_id=llmclient.id)


def _account_for(custom_domain: LLMClientCustomDomain) -> Optional[Account]:
    """Return the account that owns the custom domain."""
    user_profile = getattr(custom_domain, "user_profile", None)
    return user_profile.account if user_profile else None


def _notify(custom_domain: LLMClientCustomDomain, subject: str, body: str) -> None:
    """Email the result of the verification to the account that owns the custom domain."""
    account = _account_for(custom_domain)
    if account:
        AccountContact.send_email_to_account(account=account, subject=subject, body=body)
