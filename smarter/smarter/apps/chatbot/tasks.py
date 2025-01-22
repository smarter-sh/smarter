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

import botocore
import dns.resolver
from django.conf import settings

from smarter.apps.account.models import Account, AccountContact
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CUSTOMER_SUPPORT, SmarterEnvironments
from smarter.common.helpers.aws.exceptions import (
    AWSACMCertificateNotFound,
    AWSACMVerificationNotFound,
)
from smarter.common.helpers.aws.route53 import AWSHostedZoneNotFound
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.helpers.k8s_helpers import kubernetes_helper
from smarter.smarter_celery import app

from .exceptions import SmarterChatBotException
from .models import (
    ChatBot,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotRequests,
)


logger = logging.getLogger(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))
module_prefix = formatted_text("smarter.apps.chatbot.tasks.")


class ChatBotCustomDomainNotFound(SmarterChatBotException):
    """Raised when the custom domain for the chatbot is not found."""


class ChatBotCustomDomainExists(SmarterChatBotException):
    """Raised when the custom domain for the chatbot already exists."""


class ChatBotTaskError(SmarterChatBotException):
    """Base class for ChatBot task exceptions."""


def aggregate_chatbot_history():
    """summarize detail chatbot history into aggregate records."""

    # FIX NOTE: implement me.
    logger.info("Aggregating chatbot history.")


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def verify_certificate(certificate_arn: str):
    """Verify an AWS ACM certificate."""
    aws_helper.acm.verify_certificate(certificate_arn=certificate_arn)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_chatbot_request(chatbot_id: int, request_data: dict):
    """Create a ChatBot request record."""
    logger.info("%s - chatbot %s", module_prefix + formatted_text("create_chatbot_request()"), chatbot_id)
    chatbot = ChatBot.objects.get(id=chatbot_id)
    session_key = request_data.get("session_key")
    ChatBotRequests.objects.create(chatbot=chatbot, request=request_data, session_key=session_key)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def register_custom_domain(account_id: int, domain_name: str):
    """
    Register a customer's custom domain name in AWS Route53
    and associated the Hosted Zone with the account.
    """
    account = Account.objects.get(id=account_id)
    domain_name = aws_helper.aws.domain_resolver(domain_name)
    try:
        ChatBotCustomDomain.objects.get(account=account, domain_name=domain_name)
        certificate_arn = aws_helper.acm.get_certificate_arn(domain_name=domain_name)
        if not certificate_arn:
            raise AWSACMCertificateNotFound
        if not aws_helper.acm.certificate_is_verified(certificate_arn=certificate_arn):
            raise AWSACMVerificationNotFound

        # we found the custom domain, and its certificate is verified
        return
    except ChatBotCustomDomain.DoesNotExist:
        # the custom domain doesn't exist, so we need to create it
        pass
    except AWSACMCertificateNotFound:
        # the certificate was not found, so we need to create it
        pass
    except AWSACMVerificationNotFound:
        # the certificate has not been verified, so we need to verify it
        pass

    try:
        # verify that the domain is available to register.
        domain_record = ChatBotCustomDomain.objects.get(domain_name=domain_name)
        err = (
            "Account %s attempted to register %s but it is already registered to %s.",
            account.company_name,
            domain_name,
            domain_record.account.company_name,
        )
        logger.error(err)
        raise ChatBotCustomDomainExists(err)
    except ChatBotCustomDomain.DoesNotExist:
        # domain was not previously registered by another account, so we can continue.
        pass

    # create a Hosted Zone for the custom domain
    aws_hosted_zone, _ = aws_helper.route53.get_or_create_hosted_zone(domain_name=domain_name)
    host, _ = ChatBotCustomDomain.objects.get_or_create(
        account=account,
        domain_name=domain_name,
    )
    host.hosted_zone_id = aws_hosted_zone["Id"]
    host.save()

    # create a certificate for the custom domain
    certificate_arn = aws_helper.acm.get_or_create_certificate(domain_name=domain_name)

    # create a DNS record for the certificate and wait for it to be verified.
    aws_helper.acm.get_or_create_certificate_dns_record(certificate_arn=certificate_arn)
    verify_certificate.delay(certificate_arn=certificate_arn)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
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
    custom_domain = ChatBotCustomDomain.objects.get(id=chatbot_custom_domain_id)
    record, _ = aws_helper.route53.get_or_create_dns_record(
        hosted_zone_id=custom_domain.aws_hosted_zone_id,
        record_name=record_name,
        record_type=record_type,
        record_value=record_value,
        record_ttl=record_ttl,
    )
    dns_record, _ = ChatBotCustomDomainDNS.objects.get_or_create(
        custom_domain=custom_domain,
        record_name=record["Name"],
        record_type=record["Type"],
    )
    dns_record.record_value = record["ResourceRecords"]
    dns_record.record_ttl = record["TTL"]
    dns_record.save()


# ------------------------------------------------------------------------------
# Customer API Deployment Tasks.
# API's are deployed to the customer's default domain in Smarter, and are also
# optionally deployed to a custom domain.
# ------------------------------------------------------------------------------
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def verify_custom_domain(
    hosted_zone_id: int,
    sleep_interval: int = None,
    max_attempts: int = None,
) -> bool:
    """
    Verify the NS records of an AWS Route53 hosted zone. Custom domains
    are periodically reverified to ensure that the NS records are still valid.
    """
    fn_name = "verify_custom_domain()"
    HOURS = 24
    hosted_zone = smarter_settings.aws_route53_client.get_hosted_zone(Id=hosted_zone_id)
    domain_name = hosted_zone["HostedZone"]["Name"]
    aws_ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=hosted_zone_id)
    sleep_interval = sleep_interval or 1800
    max_attempts = max_attempts or HOURS * (3600 / sleep_interval)

    logger.info("%s - %s %s", fn_name, hosted_zone_id, domain_name)
    for i in range(max_attempts):  # 24 hours * attempts per hour * 2 days
        if i > 0:
            time.sleep(sleep_interval)  # Wait for 30 minutes before the next attempt
            logger.warning(
                "%s retrying verification of AWS Route53 Hosted Zone %s %s Attempt: %s",
                fn_name,
                hosted_zone_id,
                domain_name,
                i + 1,
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

        for record in aws_ns_records:
            aws_ns_value = record["Value"]
            if aws_ns_value in dns_ns_records:
                logger.info("%s AWS Route53 Hosted Zone %s %s verified.", fn_name, hosted_zone_id, domain_name)
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
                If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT}."""
                try:
                    account = ChatBotCustomDomain.objects.get(aws_hosted_zone_id=hosted_zone_id).account
                    AccountContact.send_email_to_account(account=account, subject=subject, body=body)
                    msg = (
                        "Domain %s has been verified for account %s %s",
                        domain_name,
                        account.company_name,
                        account.account_number,
                    )
                    logger.info(msg)
                except ChatBotCustomDomain.DoesNotExist:
                    pass

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
    If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT}."""
    account = ChatBotCustomDomain.objects.get(hosted_zone_id=hosted_zone_id).account
    AccountContact.send_email_to_account(account=account, subject=subject, body=body)

    msg = (
        "Domain verification failed for domain %s for account %s %s",
        domain_name,
        account.company_name,
        account.account_number,
    )
    logger.error(msg)

    return False


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def verify_domain(
    domain_name: str,
    record_type="A",
    chatbot: ChatBot = None,
    activate_chatbot: bool = False,
    hosted_zone_id: str = None,
) -> bool:
    """Verify that an Internet domain name resolves to NS records."""
    fn_name = "verify_domain()"

    domain_name = aws_helper.aws.domain_resolver(domain_name)
    sleep_interval = 300
    max_attempts = 48

    logger.info("%s - %s", fn_name, domain_name)
    for i in range(max_attempts):
        if i > 0:
            time.sleep(sleep_interval)
            logger.warning(
                "Retrying verification of %s. Attempt: %s",
                domain_name,
                i + 1,
            )

        # Check NS and SOA records
        try:
            # 1. verify that the DNS record actually exists. If it doesn't then there's no point in proceeding.
            if not hosted_zone_id:
                customer_api_domain_hosted_zone = aws_helper.route53.get_hosted_zone(
                    smarter_settings.customer_api_domain
                )
                hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=customer_api_domain_hosted_zone)

            dns_record = aws_helper.route53.get_dns_record(
                hosted_zone_id=hosted_zone_id, record_name=domain_name, record_type=record_type
            )
            if not dns_record:
                logger.warning(
                    "%s DNS record for domain %s not found. Nothing more to do, bailing out.", fn_name, domain_name
                )
                return False

            # 2. verify that the domain resolves to the correct NS records
            dns_ns_records = {rdata.to_text() for rdata in dns.resolver.query(domain_name)}
            logger.info("%s successfully resolved domain %s using NS records %s", fn_name, domain_name, dns_ns_records)

            if not activate_chatbot:
                return True

            # 3. if this domain is associated with a ChatBot then we should ensure that it is activated
            if chatbot:
                chatbot.deployed = True
                chatbot.save()
                logger.info("%s Chatbot %s has been deployed to %s", fn_name, chatbot.name, domain_name)
            return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            logger.warning("%s unable to resolve domain %s.", fn_name, domain_name)
            continue
        except dns.resolver.Timeout:
            logger.warning("%s timeout exceeded while querying the domain %s.", fn_name, domain_name)
            continue

    logger.error("%s unable to verify domain %s after %s attempts.", fn_name, domain_name, max_attempts)
    return False


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_domain_A_record(hostname: str, api_host_domain: str) -> dict:
    """Create an A record for the API domain."""
    fn_name = "create_domain_A_record()"
    logger.info("%s for hostname %s, api_host_domain %s", fn_name, hostname, api_host_domain)

    try:
        hostname = aws_helper.aws.domain_resolver(hostname)
        api_host_domain = aws_helper.aws.domain_resolver(api_host_domain)

        logger.info("%s resolved hostname: %s", fn_name, hostname)

        # add the A record to the customer API domain
        hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=api_host_domain)
        logger.info("%s found hosted zone %s for parent domain %s", fn_name, hosted_zone_id, api_host_domain)

        # retrieve the A record from the environment domain hosted zone. we'll
        # use this to create the A record in the customer API domain
        a_record = aws_helper.route53.get_environment_A_record(domain=api_host_domain)
        if not a_record:
            raise AWSHostedZoneNotFound(f"Hosted zone not found for domain {api_host_domain}")

        logger.info(
            "%s propagating A record %s from parent domain %s to deployment target %s",
            fn_name,
            a_record,
            api_host_domain,
            hostname,
        )

        deployment_record, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=hosted_zone_id,
            record_name=hostname,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=settings.SMARTER_CHATBOT_TASKS_DEFAULT_TTL,
        )
        verb = "Created" if created else "Verified"
        logger.info(
            "%s %s deployment DNS record %s AWS Route53 hosted zone %s %s",
            fn_name,
            verb,
            deployment_record,
            api_host_domain,
            hosted_zone_id,
        )
        return deployment_record

    except botocore.exceptions.ClientError as e:
        # If the domain already exists, we can ignore the error
        if "InvalidChangeBatch" not in str(e):
            raise
    return None


def destroy_domain_A_record(hostname: str, api_host_domain: str):
    fn_name = "destroy_domain_A_record()"
    hostname = aws_helper.aws.domain_resolver(hostname)
    api_host_domain = aws_helper.aws.domain_resolver(api_host_domain)
    logger.info("%s - %s", fn_name, hostname)

    # locate the aws route53 hosted zone for the customer API domain
    hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=api_host_domain)
    logger.info("%s found hosted zone %s for parent domain %s", fn_name, hosted_zone_id, api_host_domain)

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
        logger.error("%s a record not found for %s. Nothing to do, returning.", fn_name, api_host_domain)
        return

    print(f"{fn_name} a_record: ", a_record)
    record_type = a_record.get("Type", "A")
    record_ttl = a_record.get("TTL", settings.SMARTER_CHATBOT_TASKS_DEFAULT_TTL)
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


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def deploy_default_api(chatbot_id: int, with_domain_verification: bool = True):
    """Create a customer API default domain A record for a chatbot."""

    fn_name = "deploy_default_api()"
    logger.info("%s - chatbot %s", fn_name, chatbot_id)
    chatbot: ChatBot = None
    activate = True

    try:
        chatbot = ChatBot.objects.get(id=chatbot_id)
    except ChatBot.DoesNotExist as e:
        raise ChatBotTaskError(f"Chatbot {chatbot_id} not found.") from e

    # Prerequisites.
    # ensure that the customer API domain has an A record that we can use to create the chatbot's A record
    # our expected case is that the record already exists and that this step is benign.
    create_domain_A_record(hostname=smarter_settings.customer_api_domain, api_host_domain=smarter_settings.root_domain)

    domain_name = chatbot.default_host
    if settings.SMARTER_CHATBOT_TASKS_CREATE_DNS_RECORD:
        create_domain_A_record(hostname=domain_name, api_host_domain=smarter_settings.customer_api_domain)

    if settings.SMARTER_CHATBOT_TASKS_CREATE_DNS_RECORD and with_domain_verification:
        chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.VERIFYING
        chatbot.save()
        activate = verify_domain(domain_name, record_type="A", chatbot=chatbot, activate_chatbot=True)
        if not activate:
            chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.FAILED
            chatbot.save()

    if activate:
        chatbot.deployed = True
        chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.VERIFIED
        chatbot.save()
        logger.info("%s Chatbot %s has been deployed to %s", fn_name, chatbot.name, domain_name)

        # send an email to the account owner to notify them that the chatbot has been deployed
        subject = f"Chatbot {chatbot.name} has been deployed"
        body = f"""Your chatbot {chatbot.name} has been deployed to domain {domain_name} and is now activated
        and able to respond to prompts.\n\n
        If you also created a custom domain for your chatbot then you'll be separately notified once it has been verified.
        If you have any questions, please contact us at {SMARTER_CUSTOMER_SUPPORT}."""
        AccountContact.send_email_to_account(account=chatbot.account, subject=subject, body=body)

    # if we're running in Kubernetes then we should create an ingress manifest
    # for the customer API domain so that we can issue a certificate for it.
    if (
        settings.SMARTER_CHATBOT_TASKS_CREATE_INGRESS_MANIFEST
        and smarter_settings.environment != SmarterEnvironments.LOCAL
    ):
        logger.info("%s creating ingress manifest for %s", fn_name, domain_name)
        ingress_values = {
            "cluster_issuer": smarter_settings.customer_api_domain,
            "environment_namespace": smarter_settings.environment_namespace,
            "domain": domain_name,
            "service_name": smarter_settings.platform_name,
            "platform_url": smarter_settings.environment_url,
            "api_url": smarter_settings.customer_api_url,
        }

        # create and apply the ingress manifest
        template_path = os.path.join(HERE, "./k8s/ingress.yaml.tpl")
        with open(template_path, encoding="utf-8") as ingress_template:
            template = Template(ingress_template.read())
            manifest = template.substitute(ingress_values)
        kubernetes_helper.apply_manifest(manifest)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def undeploy_default_api(chatbot_id: int):
    """Reverse a Chatbot deployment by destroying the customer API default domain A record for a chatbot."""

    chatbot: ChatBot = None
    try:
        chatbot = ChatBot.objects.get(id=chatbot_id)
    except ChatBot.DoesNotExist:
        logger.info("Chatbot %s not found. Nothing to do, returning.", chatbot_id)

    destroy_domain_A_record(hostname=chatbot.default_host, api_host_domain=smarter_settings.customer_api_domain)

    chatbot.deployed = False
    chatbot.dns_verification_status = chatbot.DnsVerificationStatusChoices.NOT_VERIFIED
    chatbot.save()


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def deploy_custom_api(chatbot_id: int):

    chatbot = ChatBot.objects.get(id=chatbot_id)
    domain_name = chatbot.custom_domain

    if not domain_name:
        logger.warning(
            "Custom domain is missing or is not yet validated for %s chatbot %s.",
            chatbot.account.company_name,
            chatbot.name,
        )
        return

    create_domain_A_record(hostname=domain_name, api_host_domain=domain_name)

    # verify the hosted zone of the custom domain
    hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name)
    verify_custom_domain(hosted_zone_id)
