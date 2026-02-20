# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chatbot app.

These tasks are long-running and/or i/o intensive operations that are managed by Celery.
They are intended to be called asynchronously from the main application.
"""

import logging
import os
import time
from string import Template
from typing import Optional
from urllib.parse import urlparse

import dns.resolver

from smarter.apps.account.models import Account, AccountContact
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    get_cached_user_profile,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import (
    SMARTER_CHAT_SESSION_KEY_NAME,
    SMARTER_CUSTOMER_SUPPORT_EMAIL,
    SmarterEnvironments,
)
from smarter.common.helpers.aws.acm import AWSCertificateManager
from smarter.common.helpers.aws.exceptions import (
    AWSACMCertificateNotFound,
    AWSACMVerificationNotFound,
)
from smarter.common.helpers.aws.route53 import AWSRoute53
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.helpers.k8s_helpers import kubernetes_helper
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.workers.celery import app

from .exceptions import SmarterChatBotException
from .models import (
    ChatBot,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotRequests,
)
from .signals import (
    chatbot_deploy_failed,
    chatbot_deployed,
    chatbot_dns_failed,
    chatbot_dns_verification_initiated,
    chatbot_dns_verified,
    post_create_chatbot_request,
    post_create_custom_domain_dns_record,
    post_delete_default_api,
    post_deploy_custom_api,
    post_deploy_default_api,
    post_destroy_domain_A_record,
    post_register_custom_domain,
    post_undeploy_default_api,
    post_verify_certificate,
    post_verify_custom_domain,
    post_verify_domain,
    pre_create_chatbot_request,
    pre_create_custom_domain_dns_record,
    pre_delete_default_api,
    pre_deploy_custom_api,
    pre_deploy_default_api,
    pre_destroy_domain_A_record,
    pre_register_custom_domain,
    pre_undeploy_default_api,
    pre_verify_certificate,
    pre_verify_custom_domain,
    pre_verify_domain,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.TASK_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.CHATBOT_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))


def is_taskable() -> bool:
    """
    Module helper function to check if aws resources are accessible
    for task processing.
    """
    prefix = logger_prefix + f".{is_taskable.__name__}()"
    # verifies that the aws credentials are available and valid.
    if not aws_helper.ready():
        logger.debug("%s AWS helper is not ready. Request is not taskable.", prefix)
        return False

    # verify that route53 and acm helpers are available.
    if not isinstance(aws_helper.route53, AWSRoute53):
        logger.debug("%s AWS Route53 helper is not available. Request is not taskable.", prefix)
        return False

    if not isinstance(aws_helper.acm, AWSCertificateManager):
        logger.debug("%s AWS ACM helper is not available. Request is not taskable.", prefix)
        return False

    return True


class ChatBotCustomDomainNotFound(SmarterChatBotException):
    """Raised when the custom domain for the chatbot is not found."""


class ChatBotCustomDomainExists(SmarterChatBotException):
    """Raised when the custom domain for the chatbot already exists."""


class ChatBotTaskError(SmarterChatBotException):
    """Base class for ChatBot task exceptions."""


def aggregate_chatbot_history():
    """summarize detail chatbot history into aggregate records."""

    # TODO: implement me.
    logger.info("%s.aggregate_chatbot_history() - Aggregating chatbot history.", logger_prefix)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def verify_certificate(certificate_arn: str):
    """Verify an AWS ACM certificate."""
    if not is_taskable():
        return
    if not isinstance(aws_helper.acm, AWSCertificateManager):
        return False

    task_id = verify_certificate.request.id

    pre_verify_certificate.send(sender=verify_certificate, certificate_arn=certificate_arn, task_id=task_id)
    prefix = logger_prefix + ".verify_certificate()"
    logger.info("%s - %s task_id: %s", prefix, certificate_arn, task_id)

    verified = aws_helper.acm.verify_certificate(certificate_arn=certificate_arn)
    if verified:
        logger.info("%s - certificate %s verified. task_id: %s", prefix, certificate_arn, task_id)
    else:
        logger.error("%s - certificate %s verification failed. task_id: %s", prefix, certificate_arn, task_id)
    post_verify_certificate.send(sender=verify_certificate, certificate_arn=certificate_arn, task_id=task_id)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def create_chatbot_request(chatbot_id: int, request_data: dict):
    """Create a ChatBot request record."""

    task_id = create_chatbot_request.request.id
    pre_create_chatbot_request.send(
        sender=create_chatbot_request, chatbot_id=chatbot_id, request_data=request_data, task_id=task_id
    )
    logger.info(
        "%s - chatbot %s",
        logger_prefix + f".{create_chatbot_request.__name__}() task_id: %s",
        chatbot_id,
        task_id,
    )
    chatbot = ChatBot.objects.get(id=chatbot_id)
    session_key = request_data.get(SMARTER_CHAT_SESSION_KEY_NAME)
    ChatBotRequests.objects.create(chatbot=chatbot, request=request_data, session_key=session_key)
    post_create_chatbot_request.send(
        sender=create_chatbot_request, chatbot_id=chatbot_id, request_data=request_data, task_id=task_id
    )


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def register_custom_domain(account_id: int, domain_name: str):
    """
    Register a customer's custom domain name in AWS Route53
    and associated the Hosted Zone with the account.
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
    admin_user_profile = get_cached_user_profile(user=admin, account=account)  # type: ignore[assignment]
    domain_name = aws_helper.aws.domain_resolver(domain_name)

    logger.info(
        "%s - Account %s %s attempting to register custom domain %s",
        logger_prefix + f".{register_custom_domain.__name__}() task_id: %s",
        account.company_name,
        account.account_number,
        domain_name,
        task_id,
    )
    try:
        ChatBotCustomDomain.objects.get(user_profile__account=account, domain_name=domain_name)
        certificate_arn = aws_helper.acm.get_certificate_arn(domain_name=domain_name)
        if not certificate_arn:
            raise AWSACMCertificateNotFound
        if not aws_helper.acm.certificate_is_verified(certificate_arn=certificate_arn):
            raise AWSACMVerificationNotFound

        # we found the custom domain, and its certificate is verified
        logger.debug(
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
    except ChatBotCustomDomain.DoesNotExist:
        # the custom domain doesn't exist, so we need to create it
        logger.debug(
            "%s - custom domain %s not found for account %s. Proceeding to create it. task_id: %s",
            logger_prefix,
            domain_name,
            account.company_name,
            task_id,
        )
    except AWSACMCertificateNotFound:
        # the certificate was not found, so we need to create it
        logger.debug(
            "%s - certificate for domain %s not found. Proceeding to create it. task_id: %s",
            logger_prefix,
            domain_name,
            task_id,
        )
    except AWSACMVerificationNotFound:
        # the certificate has not been verified, so we need to verify it
        logger.debug(
            "%s - certificate for domain %s is not verified. Proceeding to verify it. task_id: %s",
            logger_prefix,
            domain_name,
            task_id,
        )

    try:
        # verify that the domain is available to register.
        domain_record = ChatBotCustomDomain.objects.get(domain_name=domain_name)
        err = f"{logger_prefix}.register_custom_domain() - Account {account.company_name} attempted to register {domain_name} but it is already registered to {domain_record.account.company_name} task_id: {task_id}"
        logger.error(err)
        raise ChatBotCustomDomainExists(err)
    except ChatBotCustomDomain.DoesNotExist:
        # domain was not previously registered by another account, so we can continue.
        logger.debug("%s - domain %s is available to register. task_id: %s", logger_prefix, domain_name, task_id)

    # create a Hosted Zone for the custom domain

    aws_hosted_zone, _ = aws_helper.route53.get_or_create_hosted_zone(domain_name=domain_name)
    host, _ = ChatBotCustomDomain.objects.get_or_create(
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


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def create_custom_domain_dns_record(
    chatbot_custom_domain_id: int, record_name: str, record_type: str, record_value: str, record_ttl: int = 600
):
    """
    Get or create a DNS record in an AWS Route53 hosted zone.
    example return value:
        {
            'Name': 'example.com.',
            'Type': 'A',
            'TTL': 300,
            'ResourceRecords': [
                {
                    'Value': '192.0.2.44'
                },
            ],
        }
    """
    if not is_taskable():
        return
    if not isinstance(aws_helper.route53, AWSRoute53):
        return

    task_id = create_custom_domain_dns_record.request.id

    logger.info(
        "%s - creating DNS record %s %s for ChatBotCustomDomain %s",
        logger_prefix + ".create_custom_domain_dns_record() task_id: %s",
        record_type,
        record_name,
        chatbot_custom_domain_id,
        task_id,
    )

    pre_create_custom_domain_dns_record.send(
        sender=create_custom_domain_dns_record,
        chatbot_custom_domain_id=chatbot_custom_domain_id,
        record_name=record_name,
        record_type=record_type,
        record_value=record_value,
        record_ttl=record_ttl,
        task_id=task_id,
    )
    try:
        custom_domain = ChatBotCustomDomain.objects.get(id=chatbot_custom_domain_id)
    except ChatBotCustomDomain.DoesNotExist as e:
        err = f"{logger_prefix}.create_custom_domain_dns_record() - ChatBotCustomDomain {chatbot_custom_domain_id} not found. task_id: {task_id}"
        logger.error(err)
        raise ChatBotCustomDomainNotFound(err) from e

    record, _ = aws_helper.route53.get_or_create_dns_record(
        hosted_zone_id=custom_domain.aws_hosted_zone_id,
        record_name=record_name,
        record_type=record_type,
        record_value=record_value,
        record_ttl=record_ttl,
    )
    try:
        # note: we cannot use the get_or_create method here because
        # of validation errors that are raised if record_value is
        # not present.
        dns_record = ChatBotCustomDomainDNS.objects.get(
            custom_domain=custom_domain,
            record_name=record["Name"],
            record_type=record["Type"],
        )
        dns_record.record_value = (record["ResourceRecords"],)
        dns_record.record_ttl = (record["TTL"],)
        dns_record.save()
    except ChatBotCustomDomainDNS.DoesNotExist:
        dns_record = ChatBotCustomDomainDNS(
            custom_domain=custom_domain,
            record_name=record["Name"],
            record_type=record["Type"],
            record_value=record["ResourceRecords"],
            record_ttl=record["TTL"],
        )

    post_create_custom_domain_dns_record.send(
        sender=create_custom_domain_dns_record,
        chatbot_custom_domain_id=chatbot_custom_domain_id,
        record_name=record_name,
        record_type=record_type,
        record_value=record_value,
        record_ttl=record_ttl,
        task_id=task_id,
    )


# ------------------------------------------------------------------------------
# Customer API Deployment Tasks.
# API's are deployed to the customer's default domain in Smarter, and are also
# optionally deployed to a custom domain.
# ------------------------------------------------------------------------------
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def verify_custom_domain(
    hosted_zone_id: str,
    sleep_interval: Optional[int] = None,
    max_attempts: Optional[int] = None,
) -> bool:
    """
    Verify the NS records of an AWS Route53 hosted zone. Custom domains
    are periodically reverified to ensure that the NS records are still valid.
    """
    if not is_taskable():
        return False
    if not aws_helper.route53:
        return False

    fn_name = logger_prefix + ".verify_custom_domain()"
    task_id = verify_custom_domain.request.id
    logger.info(
        "%s - verifying AWS Route53 Hosted Zone %s task_id: %s",
        fn_name,
        hosted_zone_id,
        task_id,
    )

    pre_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)

    HOURS = 24
    hosted_zone = aws_helper.route53.get_hosted_zone_by_id(hosted_zone_id=hosted_zone_id)
    if not isinstance(hosted_zone, dict):
        raise ChatBotTaskError(f"expected a dict but received {type(hosted_zone)}")
    domain_name = hosted_zone["HostedZone"]["Name"]
    aws_ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=hosted_zone_id)
    sleep_interval = sleep_interval or 1800
    max_attempts = max_attempts or int(HOURS * (3600 / sleep_interval))

    logger.info("%s - %s %s", fn_name, hosted_zone_id, domain_name)
    for i in range(max_attempts):  # 24 hours * attempts per hour * 2 days
        if i > 0:
            time.sleep(sleep_interval)  # Wait for 30 minutes before the next attempt
            logger.warning(
                "%s retrying verification of AWS Route53 Hosted Zone %s %s Attempt: %s of %s task_id: %s",
                fn_name,
                hosted_zone_id,
                domain_name,
                i + 1,
                max_attempts,
                task_id,
            )

        # Check NS and SOA records
        try:
            dns_ns_records = {rdata.to_text() for rdata in dns.resolver.query(domain_name, "NS")}
        except dns.resolver.NXDOMAIN:
            logger.warning("%s domain %s does not exist.", fn_name, domain_name)
            continue
        except dns.resolver.Timeout:
            logger.warning("%s timeout exceeded while querying the domain %s.", fn_name, domain_name)
            continue
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s unexpected error while querying domain %s: %s", fn_name, domain_name, str(e))
            continue

        j = 0
        for record in aws_ns_records:
            j += 1
            logger.info(
                "%s checking AWS NS record %s (%s of %s) against DNS NS records %s task_id: %s",
                fn_name,
                record["Value"],
                j,
                len(aws_ns_records),
                dns_ns_records,
                task_id,
            )
            aws_ns_value = record["Value"]
            if aws_ns_value in dns_ns_records:
                logger.info(
                    "%s AWS Route53 Hosted Zone %s %s verified. task_id %s",
                    fn_name,
                    hosted_zone_id,
                    domain_name,
                    task_id,
                )
                # if this is a customer custom domain, we should update the database to reflect that
                # the domain is verified.
                try:
                    custom_domain = ChatBotCustomDomain.objects.get(aws_hosted_zone_id=hosted_zone_id)
                    custom_domain.is_verified = True
                    custom_domain.save()
                except ChatBotCustomDomain.DoesNotExist:
                    logger.info("%s domain %s is not a ChatBot custom domain.", fn_name, domain_name)

                # send an email to the account owner to notify them that the domain has been verified
                subject = f"Domain Verification for {domain_name} Successful"
                body = f"""Your domain {domain_name} has been verified.\n\n
                Your custom domain is now active and ready to use with your ChatBot.
                If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."""
                try:
                    account = ChatBotCustomDomain.objects.get(aws_hosted_zone_id=hosted_zone_id).account
                    AccountContact.send_email_to_account(account=account, subject=subject, body=body)
                    msg = f"{fn_name} - Domain {domain_name} has been verified for account {account.company_name} {account.account_number} task_id: {task_id}"
                    logger.info(msg)
                except ChatBotCustomDomain.DoesNotExist:
                    pass

                post_verify_custom_domain.send(
                    sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id
                )
                return True

        # If we get here, then the hosted zone is not verified
        # and we should update the custom domain record to reflect that.
        try:
            hosted_zone = ChatBotCustomDomain.objects.get(aws_hosted_zone_id=hosted_zone_id, is_verified=True)
            hosted_zone.is_verified = False
            hosted_zone.save()
        except ChatBotCustomDomain.DoesNotExist:
            continue

    # send an email to the account owner to notify them that the domain verification failed
    subject = f"Domain Verification Failure for {domain_name}"
    body = f"""We were unable to verify your domain {domain_name}.\n\n
    We made {max_attempts} attempts over a period of {HOURS} hours to verify the domain.
    If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT_EMAIL}."""
    account = ChatBotCustomDomain.objects.get(hosted_zone_id=hosted_zone_id).account
    AccountContact.send_email_to_account(account=account, subject=subject, body=body)
    msg = f"{fn_name} - Domain verification failed for domain {domain_name} for account {account.company_name} {account.account_number} task_id: {task_id}"
    logger.error(msg)
    post_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id, task_id=task_id)
    return False


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def verify_domain(
    domain_name: str,
    record_type="A",
    chatbot: Optional[ChatBot] = None,
    activate_chatbot: bool = False,
    hosted_zone_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> bool:
    """
    Verify that an Internet domain name resolves to NS records.

    Signals:
    chatbot_dns_verification_initiated
    chatbot_dns_failed,
    chatbot_dns_verified,
    """
    if not is_taskable():
        return False
    if not aws_helper.route53:
        return False

    fn_name = f"{logger_prefix}.verify_domain()"
    task_id = verify_domain.request.id or task_id
    logger.info("%s - verifying domain %s task_id: %s", fn_name, domain_name, task_id)

    pre_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
    chatbot_dns_verification_initiated.send(
        sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
    )

    domain_name = aws_helper.aws.domain_resolver(domain_name)
    sleep_interval = 300
    max_attempts = 48

    for i in range(max_attempts):
        logger.info(
            "%s - Attempt %s of %s to verify domain %s task_id: %s",
            fn_name,
            i + 1,
            max_attempts,
            domain_name,
            task_id,
        )
        if i > 0:
            time.sleep(sleep_interval)
            logger.warning(
                "%s Retrying verification of %s. Attempt: %s task_id: %s",
                fn_name,
                domain_name,
                i + 1,
                task_id,
            )

        # Check NS and SOA records
        try:
            # 1. verify that the DNS record actually exists. If it doesn't then there's no point in proceeding.
            if not hosted_zone_id:
                customer_api_domain_hosted_zone = aws_helper.route53.get_hosted_zone(
                    smarter_settings.environment_api_domain
                )
                hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=customer_api_domain_hosted_zone)

            dns_record = aws_helper.route53.get_dns_record(
                hosted_zone_id=hosted_zone_id, record_name=domain_name, record_type=record_type
            )
            if not dns_record:
                logger.warning(
                    "%s DNS record for domain %s not found. Nothing more to do, bailing out. task_id: %s",
                    fn_name,
                    domain_name,
                    task_id,
                )
                if chatbot:
                    chatbot_dns_failed.send(
                        sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
                    )
                    chatbot.dns_verification_status = ChatBot.DNS_VERIFICATION_FAILED
                    chatbot.save(asynchronous=True)
                post_verify_domain.send(
                    sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
                )
                return False

            # 2. verify that the domain resolves to the correct NS records
            dns_ns_records = {rdata.to_text() for rdata in dns.resolver.query(domain_name)}
            logger.info(
                "%s successfully resolved domain %s using NS records %s task_id: %s",
                fn_name,
                domain_name,
                dns_ns_records,
                task_id,
            )
            chatbot_dns_verified.send(
                sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
            )

            if not activate_chatbot:
                post_verify_domain.send(
                    sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
                )
                return True

            # 3. if this domain is associated with a ChatBot then we should ensure that it is activated
            if chatbot and not chatbot.deployed:
                chatbot.deployed = True
                chatbot.save(asynchronous=True)
                logger.info(
                    "%s Chatbot %s has been deployed to %s task_id: %s", fn_name, chatbot.name, domain_name, task_id
                )

            post_verify_domain.send(
                sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
            )
            return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            logger.warning("%s unable to resolve domain %s task_id: %s", fn_name, domain_name, task_id)
            chatbot_dns_failed.send(
                sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
            )
            continue
        except dns.resolver.Timeout:
            logger.warning(
                "%s timeout exceeded while querying the domain %s task_id: %s", fn_name, domain_name, task_id
            )
            chatbot_dns_failed.send(
                sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id
            )
            continue

    logger.error(
        "%s unable to verify domain %s after %s attempts task_id: %s", fn_name, domain_name, max_attempts, task_id
    )
    post_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
    chatbot_dns_failed.send(sender=verify_domain, domain_name=domain_name, record_type=record_type, task_id=task_id)
    return False


def destroy_domain_A_record(hostname: str, api_host_domain: str):
    """Destroy the A record for a domain name."""
    if not is_taskable():
        return
    if not aws_helper.route53:
        return

    task_id = destroy_domain_A_record.request.id
    pre_destroy_domain_A_record.send(
        sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain, task_id=task_id
    )

    fn_name = logger_prefix + ".destroy_domain_A_record()"
    hostname = aws_helper.aws.domain_resolver(hostname)
    api_host_domain = aws_helper.aws.domain_resolver(api_host_domain)
    logger.info("%s - %s task_id: %s", fn_name, hostname, task_id)

    # locate the aws route53 hosted zone for the customer API domain
    hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=api_host_domain)
    logger.info(
        "%s found hosted zone %s for parent domain %s task_id: %s", fn_name, hosted_zone_id, api_host_domain, task_id
    )

    # retrieve the A record from the environment domain hosted zone. we'll
    # use this to create the A record in the customer API domain. example:
    # {
    #     "Name": "example.com.",
    #     "Type": "A",
    #     "TTL": 300,
    #     "ResourceRecords": [{"Value": "192.1.1.1"}]
    # }

    a_record = aws_helper.route53.get_dns_record(
        hosted_zone_id=hosted_zone_id,
        record_name=hostname,
        record_type="A",
    )
    if not a_record:
        logger.error(
            "%s a record not found for %s. Nothing to do, returning. task_id: %s", fn_name, api_host_domain, task_id
        )
        post_destroy_domain_A_record.send(
            sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain
        )
        return

    logger.info(f"{fn_name} a_record: {a_record}")
    record_type = a_record.get("Type", "A")
    record_ttl = a_record.get("TTL", smarter_settings.chatbot_tasks_default_ttl)
    alias_target = a_record.get("AliasTarget")
    record_resource_records = a_record.get("ResourceRecords")
    aws_helper.route53.destroy_dns_record(
        hosted_zone_id=hosted_zone_id,
        record_name=hostname,
        record_type=record_type,
        record_ttl=record_ttl,
        alias_target=alias_target,
        record_resource_records=record_resource_records,
    )
    post_destroy_domain_A_record.send(
        sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain, task_id=task_id
    )


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def deploy_default_api(chatbot_id: int, with_domain_verification: bool = True):
    """
    Create a customer API default domain A record for a chatbot.

    Signals:
    ------------------------------
    pre_deploy_default_api
    post_deploy_default_api
    chatbot_dns_verification_initiated,
    chatbot_dns_verified,
    chatbot_dns_failed,
    chatbot_dns_verification_status_changed,

    """
    if not is_taskable():
        return

    fn_name = logger_prefix + ".deploy_default_api()"
    task_id = deploy_default_api.request.id
    logger.info("%s - chatbot %s task_id: %s", fn_name, chatbot_id, task_id)
    chatbot: ChatBot
    activate = False

    pre_deploy_default_api.send(
        sender=deploy_default_api,
        chatbot_id=chatbot_id,
        with_domain_verification=with_domain_verification,
        task_id=task_id,
    )

    try:
        chatbot = ChatBot.objects.get(id=chatbot_id)
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

    # Prerequisites.
    # ensure that the root API domain has an A record that we can use to create the chatbot's A record
    # our expected case is that the record already exists and that this step is benign.
    aws_helper.route53.create_domain_a_record(
        hostname=smarter_settings.environment_api_domain, api_host_domain=smarter_settings.root_api_domain
    )

    domain_name = chatbot.default_host
    if smarter_settings.chatbot_tasks_create_dns_record:
        aws_helper.route53.create_domain_a_record(
            hostname=domain_name, api_host_domain=smarter_settings.environment_api_domain
        )

    if smarter_settings.chatbot_tasks_create_dns_record and with_domain_verification:
        chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.VERIFYING
        chatbot.save(asynchronous=True)
        activate = verify_domain(domain_name, record_type="A", chatbot=chatbot, activate_chatbot=True, task_id=task_id)
        if not activate:
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
    else:
        activate = True

    if activate:
        chatbot.deployed = True
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
        AccountContact.send_email_to_primary_contact(account=chatbot.user_profile.account, subject=subject, body=body)
    else:
        logger.error(
            "%s unable to verify domain %s. Chatbot %s will not be deployed. task_id: %s",
            fn_name,
            domain_name,
            chatbot.name,
            task_id,
        )
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

    # if we're running in Kubernetes then we should create an ingress manifest
    # for the customer API domain so that we can issue a certificate for it.
    if (
        smarter_settings.chatbot_tasks_create_ingress_manifest
        and smarter_settings.environment != SmarterEnvironments.LOCAL
    ):
        logger.info("%s verifying/creating ingress manifest for %s task_id: %s", fn_name, domain_name, task_id)
        ingress_values = {
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
        kubernetes_helper.apply_manifest(manifest)

        if chatbot.tls_certificate_issuance_status != chatbot.TlsCertificateIssuanceStatusChoices.ISSUED:
            # move ourselves back to the first step in the process.
            chatbot.tls_certificate_issuance_status = chatbot.TlsCertificateIssuanceStatusChoices.REQUESTED
            chatbot.save(asynchronous=True)
            wait_time = 300
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


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def undeploy_default_api(chatbot_id: int):
    """Reverse a Chatbot deployment by destroying the customer API default domain A record for a chatbot."""
    if not is_taskable():
        return

    task_id = undeploy_default_api.request.id
    prefix = logger_prefix + f".{undeploy_default_api.__name__}()"
    logger.info("%s - chatbot %s task_id: %s", prefix, chatbot_id, task_id)
    pre_undeploy_default_api.send(sender=undeploy_default_api, chatbot_id=chatbot_id, task_id=task_id)

    chatbot: ChatBot
    try:
        chatbot = ChatBot.objects.get(id=chatbot_id)
    except ChatBot.DoesNotExist:
        logger.error("%s Chatbot %s not found. task_id: %s", prefix, chatbot_id, task_id)
        post_undeploy_default_api.send(sender=undeploy_default_api, chatbot_id=chatbot_id)
        return None

    chatbot.deployed = False
    chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.NOT_VERIFIED
    chatbot.save(asynchronous=True)
    post_undeploy_default_api.send(sender=undeploy_default_api, chatbot_id=chatbot_id, task_id=task_id)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def delete_default_api(url: str, account_number: str, name: str):
    """
    Delete aws resources for a customer API
    - delete default domain Route53 A record for a chatbot.
    - delete ingress resources: ingress, certificate, secret.
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
    destroy_domain_A_record(hostname=hostname, api_host_domain=smarter_settings.environment_api_domain)
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


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.chatbot_tasks_celery_retry_backoff,
    max_retries=smarter_settings.chatbot_tasks_celery_max_retries,
    queue=smarter_settings.chatbot_tasks_celery_task_queue,
)
def deploy_custom_api(chatbot_id: int):
    """Create a customer API custom domain A record for a chatbot."""
    pre_deploy_custom_api.send(sender=deploy_custom_api, chatbot_id=chatbot_id)
    prefix = logger_prefix + f".{deploy_custom_api.__name__}()"
    task_id = deploy_custom_api.request.id
    logger.info("%s - chatbot %s task_id: %s", prefix, chatbot_id, task_id)

    chatbot = ChatBot.objects.get(id=chatbot_id)
    domain_name = chatbot.custom_domain

    if not domain_name:
        logger.warning(
            "%s Custom domain is missing or is not yet validated for %s chatbot %s task_id: %s. Nothing to do, returning.",
            prefix,
            chatbot.account.company_name,
            chatbot.name,
            task_id,
        )
        post_deploy_custom_api.send(sender=deploy_custom_api, chatbot_id=chatbot_id, task_id=task_id)
        return

    if not is_taskable():
        return

    aws_helper.route53.create_domain_a_record(hostname=domain_name, api_host_domain=domain_name)  # type: ignore[union-attr]

    # verify the hosted zone of the custom domain
    hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name)  # type: ignore[union-attr]
    verify_custom_domain(hosted_zone_id)
    post_deploy_custom_api.send(sender=deploy_custom_api, chatbot_id=chatbot_id, task_id=task_id)
