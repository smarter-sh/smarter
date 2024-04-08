# -*- coding: utf-8 -*-
"""This module is used to initialize the environment."""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand

from smarter.common.aws import aws_helper
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN


# pylint: disable=E1101
class Command(BaseCommand):
    """Verify AWS resources for hosting customer api's."""

    log_prefix = "manage.py initialize_api_infrastructure:"

    def verify(self, domain: str):
        """
        Verify the AWS resources for hosting the customer api and the web platform.
         - api.smarter.sh, alpha.api.smarter.sh, beta.api.smarter.sh, etc.
         - platform.smarter.sh, alpha.platform.smarter.sh, beta.platform.smarter.sh, etc.
        """
        # 1. Verify the AWS Route53 hosted zone for the domain
        # ---------------------------------------------------------------------
        customer_api_domain_hosted_zone, _ = aws_helper.get_or_create_hosted_zone(domain_name=domain)
        hosted_zone_id = aws_helper.get_hosted_zone_id(hosted_zone=customer_api_domain_hosted_zone)
        print(f"{self.log_prefix} Found AWS Route53 hosted zone {hosted_zone_id} for domain: {domain}")

        # 2. Verify the NS records for the domain in the root domain's hosted zone
        # ---------------------------------------------------------------------
        ns_records = aws_helper.get_ns_records(hosted_zone_id=hosted_zone_id)
        print(f"{self.log_prefix} found NS Records: {ns_records}")

        root_domain_hosted_zone_id = aws_helper.get_hosted_zone_id_for_domain(domain_name=smarter_settings.root_domain)
        print(
            f"{self.log_prefix} found Hosted Zone {root_domain_hosted_zone_id} for root domain {smarter_settings.root_domain}"
        )

        ns_record = aws_helper.get_or_create_dns_record(
            hosted_zone_id=root_domain_hosted_zone_id,
            record_name=domain,
            record_type="NS",
            record_value=ns_records,
            record_ttl=300,
        )
        print(
            f"{self.log_prefix} verified NS Records for {domain} in hosted zone for root domain {smarter_settings.root_domain}: {ns_record}"
        )

        # 3. Verify the A record for the domain
        # ---------------------------------------------------------------------
        environments = [
            f"{SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
            f"alpha.{SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
            f"beta.{SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
            f"next.{SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
        ]
        for environment_domain in environments:
            print(f"looking for an A record in {environment_domain}...")
            a_record = aws_helper.get_environment_A_record(domain=environment_domain)
            if a_record:
                print(f"{self.log_prefix} verifying {domain} A record against domain: ", environment_domain)
                print(f"{self.log_prefix} A record: {a_record}")
                break

        if not a_record:
            raise ImproperlyConfigured(
                f"{self.log_prefix} Checked the following domains: {environments} but couldn't find an A record to propagate to domain: {domain}. Cannot proceed."
            )

        this_a_record = aws_helper.get_or_create_dns_record(
            hosted_zone_id=hosted_zone_id,
            record_name=domain,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=600,
        )
        print(f"{self.log_prefix} verified A record for {domain}: {this_a_record}")

    def handle(self, *args, **options):
        print(f"{self.log_prefix} Initializing api aws infrastructure for environment...")
        print("*" * 80)
        self.verify(domain=smarter_settings.customer_api_domain)
        self.verify(domain=smarter_settings.environment_domain)
        print("*" * 80)
        print(f"{self.log_prefix} aws infrastructure for customer api hosting is initialized and configured.")
