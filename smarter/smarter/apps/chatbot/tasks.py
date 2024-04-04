# -*- coding: utf-8 -*-
# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for chatbot app.

These tasks are long-running and/or i/o intensive operations that are managed by Celery.
They are intended to be called asynchronously from the main application.
"""
import logging
import socket
import time

import botocore
import dns.resolver

from smarter.apps.account.models import Account
from smarter.common.aws import aws_helper
from smarter.common.conf import settings as smarter_settings
from smarter.smarter_celery import app

from .models import ChatBot, ChatBotCustomDomain, ChatBotCustomDomainDNS


logger = logging.getLogger(__name__)

DEFAULT_TTL = 600


@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def create_custom_domain(account_id: int, domain_name: str) -> bool:
    """
    Register a customer's custom domain name in AWS Route53
    and associated the Hosted Zone with the account.
    """
    account = Account.objects.get(id=account_id)
    try:
        ChatBotCustomDomain.objects.get(account=account, domain_name=domain_name)
    except ChatBotCustomDomain.DoesNotExist:
        # we've already created the hosted zone for this domain
        return True

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
        raise ValueError(err)
    except ChatBotCustomDomain.DoesNotExist:
        # domain was not previously registered, so we can continue.
        pass

    aws_hosted_zone, _ = aws_helper.get_or_create_hosted_zone(domain_name=domain_name)

    host = ChatBotCustomDomain.objects.get_or_create(
        account=account,
        domain_name=domain_name,
    )
    host.hosted_zone_id = aws_hosted_zone["Id"]
    host.save()

    return True


@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def create_custom_domain_dns_record(
    dns_host_id: int, record_name: str, record_type: str, record_value: str, record_ttl: int = 600
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
    dns_host = ChatBotCustomDomain.objects.get(id=dns_host_id)
    record = aws_helper.get_or_create_dns_record(
        hosted_zone_id=dns_host.aws_hosted_zone_id,
        record_name=record_name,
        record_type=record_type,
        record_value=record_value,
        record_ttl=record_ttl,
    )
    dns_record = ChatBotCustomDomainDNS.objects.get_or_create(
        dns_host=dns_host,
        record_name=record["Name"],
        record_type=record["Type"],
    )
    dns_record.record_value = record["Value"]
    dns_record.record_ttl = record["TTL"]
    dns_record.save()


# ------------------------------------------------------------------------------
# Customer API Deployment Tasks.
# API's are deployed to the customer's default domain in Smarter, and are also
# optionally deployed to a custom domain.
# ------------------------------------------------------------------------------
@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def verify_custom_domain(hosted_zone_id: int) -> bool:
    """Verify the NS records of an AWS Route53 hosted zone."""

    response = smarter_settings.aws_route53_client.get_hosted_zone(Id=hosted_zone_id)
    domain_name = response["HostedZone"]["Name"]
    aws_ns_records = set(response["DelegationSet"]["NameServers"])
    ns_is_reachable = False
    sleep_interval = 1800
    max_attempts = int(24 * (3600 / sleep_interval) * 2)

    for i in range(max_attempts):  # 24 hours * attempts per hour * 2 days
        if i > 0:
            time.sleep(sleep_interval)  # Wait for 30 minutes before the next attempt
            logger.warning(
                "Retrying verification of AWS Route53 Hosted Zone %s %s. Attempt: %s",
                hosted_zone_id,
                domain_name,
                i + 1,
            )

        # verify that we can reach the nameservers
        for ns in aws_ns_records:
            try:
                socket.gethostbyname(ns)
                ns_is_reachable = True
            except socket.gaierror:
                logger.warning("Nameserver %s is not reachable.", ns)
        if not ns_is_reachable:
            continue

        # Check NS and SOA records
        domain = response["HostedZone"]["Name"]
        try:
            dns_ns_records = set(rdata.to_text() for rdata in dns.resolver.query(domain, "NS"))
        except dns.resolver.NXDOMAIN:
            logger.warning("Domain %s does not exist.", domain_name)
            continue
        except dns.resolver.Timeout:
            logger.warning("Timeout while querying the domain %s.", domain_name)
            continue

        for record in aws_ns_records:
            if record in dns_ns_records:
                logger.info("AWS Route53 Hosted Zone %s %s verified.", hosted_zone_id, domain_name)
                hosted_zone = ChatBotCustomDomain.objects.get(aws_hosted_zone_id=hosted_zone_id)
                hosted_zone.is_verified = True
                hosted_zone.save()
                return True

        # If we get here, then the hosted zone is not verified
        # and we should update the database to reflect that.
        try:
            hosted_zone = ChatBotCustomDomain.objects.get(aws_hosted_zone_id=hosted_zone_id, is_verified=True)
            hosted_zone.is_verified = False
            hosted_zone.save()
        except ChatBotCustomDomain.DoesNotExist:
            continue

    return False


@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def verify_domain(domain_name: str) -> bool:
    """Verify that an Internet domain name resolves to NS records."""
    sleep_interval = 300
    max_attempts = 48

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
            dns_ns_records = set(rdata.to_text() for rdata in dns.resolver.query(domain_name))
            logger.info("Found NS records %s for domain %s", dns_ns_records, domain_name)
            return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            logger.warning("Domain %s does not exist.", domain_name)
            continue
        except dns.resolver.Timeout:
            logger.warning("Timeout while querying the domain %s.", domain_name)
            continue

    return False


def create_domain_A_record(fqdn: str, api_host_domain: str):
    """Create an A record for the API domain."""

    try:
        logger.info("Deploying %s", fqdn)

        # add the A record to the customer API domain
        hosted_zone_id = aws_helper.get_hosted_zone_id_for_domain(domain_name=api_host_domain)
        logger.info("Found hosted zone %s for parent domain %s", hosted_zone_id, api_host_domain)

        # retrieve the A record from the environment domain hosted zone. we'll
        # use this to create the A record in the customer API domain
        a_record = aws_helper.get_environment_A_record(domain=api_host_domain)
        logger.info(
            "Propagating A record %s for parent domain %s to deployment target %s", a_record, api_host_domain, fqdn
        )

        deployment_record = aws_helper.get_or_create_dns_record(
            hosted_zone_id=hosted_zone_id,
            record_name=fqdn,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=DEFAULT_TTL,
        )

        logger.info(
            "Verified deployment DNS record %s AWS Route53 hosted zone %s %s",
            deployment_record,
            api_host_domain,
            hosted_zone_id,
        )

    except botocore.exceptions.ClientError as e:
        # If the domain already exists, we can ignore the error
        if "InvalidChangeBatch" not in str(e):
            raise


@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def deploy_default_api(chatbot_id: int):
    """Create a customer API default domain A record for a chatbot."""
    chatbot = ChatBot.objects.get(id=chatbot_id)
    domain_name = chatbot.default_domain
    create_domain_A_record(fqdn=domain_name, api_host_domain=smarter_settings.customer_api_domain)
    if verify_domain(domain_name):
        chatbot.deployed = True
        chatbot.save()
        logger.info("%s chatbot %s has been deployed to %s", chatbot.account.company_name, chatbot.name, domain_name)


@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
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

    create_domain_A_record(fqdn=domain_name, api_host_domain=domain_name)

    # verify the hosted zone of the custom domain
    hosted_zone_id = aws_helper.get_hosted_zone_id_for_domain(domain_name)
    verify_custom_domain(hosted_zone_id)
