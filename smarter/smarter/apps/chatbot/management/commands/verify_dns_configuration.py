"""This module is used to initialize the environment."""

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import (
    SMARTER_API_SUBDOMAIN,
    SMARTER_PLATFORM_SUBDOMAIN,
    SmarterEnvironments,
)
from smarter.common.helpers.aws_helpers import aws_helper


ALL_DOMAINS = [
    smarter_settings.root_domain,
    smarter_settings.api_domain,
    smarter_settings.platform_domain,
    f"{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
    f"{SmarterEnvironments.ALPHA}.{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
    f"{SmarterEnvironments.BETA}.{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
    f"{SmarterEnvironments.NEXT}.{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
    f"{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
    f"{SmarterEnvironments.ALPHA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
    f"{SmarterEnvironments.BETA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
    f"{SmarterEnvironments.NEXT}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
]


# pylint: disable=E1101
class Command(BaseCommand):
    """
    Verify AWS resources for hosting customer api's.
    - api.smarter.sh, alpha.api.smarter.sh, beta.api.smarter.sh, etc.
    - platform.smarter.sh, alpha.platform.smarter.sh, beta.platform.smarter.sh, etc.

    """

    log_prefix = "manage.py verify_dns_configuration()"

    def get_ns_records_for_domain(self, domain: str) -> dict:
        """
        helper to find NS records for a hosted zone.

        returns a dict of this form:
            {
                "Name": "example.com.",
                "Type": "NS",
                "TTL": 600,
                "ResourceRecords": [
                    {
                        "Value": "ns-2048.awsdns-64.com"
                    },
                    {
                        "Value": "ns-2049.awsdns-65.net"
                    },
                    {
                        "Value": "ns-2050.awsdns-66.org"
                    },
                    {
                        "Value": "ns-2051.awsdns-67.co.uk"
                    }
                ]
            }
        """
        domain = aws_helper.aws.domain_resolver(domain)
        hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=domain)
        ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=hosted_zone_id)
        # noting that a hosted zone can have multiple NS records, we need to find
        # the NS records for the domain of the hosted zone itself.
        return next((item for item in ns_records if item["Name"] in [domain, f"{domain}."]), None)

    def get_an_A_record(self) -> dict:
        for some_domain in ALL_DOMAINS:
            print(f"looking for an A record in {some_domain}...")
            a_record = aws_helper.route53.get_environment_A_record(domain=some_domain)
            if a_record:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"get_an_A_record() found an A record in the hosted zone for domain: {a_record['Name']}"
                    )
                )
                return a_record

        raise ImproperlyConfigured(
            f"get_an_A_record() Checked the following domains: {ALL_DOMAINS} but couldn't find an A record to propagate. Cannot proceed."
        )

    # pylint: disable=R0912,R0915
    def verify_base_dns_config(self):
        """
        1. Verify the AWS Route53 hosted zone for the root domain. ie smarter.sh
            - hosted zone for root domain should exist.
            - hosted zone should contain A record alias to the AWS Classic Load Balancer.
            - hosted zone should contain NS records for 'domain'.
            - hosted zone should contain CNAME record for _acme-challenge pointing to 'domain'.
        2. Verify the AWS Route53 hosted zone for 'api'. ie api.smarter.sh
            - hosted zone for 'api.smarter.sh' should exist.
            - hosted zone should contain A record alias to the AWS Classic Load Balancer.
        3. Verify the AWS Route53 hosted zone for 'platform'. ie platform.smarter.sh
            - hosted zone for 'platform.smarter.sh' should exist.
            - hosted zone should contain A record alias to the AWS Classic Load Balancer.
        """

        log_prefix = self.log_prefix + " - " + "verify_base_dns_config()"
        print("-" * 80)
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verifying DNS configuration for {smarter_settings.root_domain}, {smarter_settings.platform_domain} and {smarter_settings.api_domain}"
            )
        )
        print("-" * 80)

        # 1. Root domain hosted zone verification, ie smarter.sh
        # ---------------------------------------------------------------------
        # Look for an A record in the root domain hosted zone
        self.stdout.write(
            self.style.NOTICE(f"{log_prefix} (1) root domain DNS verification: {smarter_settings.root_domain}")
        )
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that a hosted zone exists for the root domain: {smarter_settings.root_domain}"
            )
        )
        if not aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=smarter_settings.root_domain):
            raise ImproperlyConfigured(
                f"{self.log_prefix} AWS Route53 hosted zone for root domain: {smarter_settings.root_domain} does not exist. Cannot proceed."
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"{self.log_prefix}: verified AWS Route53 hosted zone for the root domain: {smarter_settings.root_domain}."
            )
        )

        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that an A record exists in hosted zone for {smarter_settings.root_domain}"
            )
        )
        a_record = aws_helper.route53.get_environment_A_record(domain=smarter_settings.root_domain)
        if not a_record:
            raise ImproperlyConfigured(
                f"{log_prefix} Couldn't find an A record in the root domain: "
                f"{smarter_settings.root_domain}. Expected to find an 'A' record alias to an AWS Route53 "
                "classic balancer. Cannot proceed."
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"{log_prefix} found a propagatable A record in the hosted zone for domain: {a_record['Name']}"
            )
        )

        # check NS records in the root domain hosted zone
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that we can retrieve a list of NS records from hosted zone for {smarter_settings.root_domain}"
            )
        )
        root_domain_hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(
            domain_name=smarter_settings.root_domain
        )
        ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=root_domain_hosted_zone_id)
        # we're expecting three sets of NS records, for root, api, platform.
        if not isinstance(ns_records, list):
            raise ImproperlyConfigured(
                f"{log_prefix} Expected to find a list of NS records in the root domain hosted zone but got: {type(ns_records)}. Cannot proceed."
            )
        additional_ns_records = [
            record["Name"]
            for record in ns_records
            if record["Name"] not in [smarter_settings.root_domain, f"{smarter_settings.root_domain}."]
        ]
        self.stdout.write(
            self.style.SUCCESS(
                f"{log_prefix} found {len(ns_records) - 1} sets of NS records in the hosted zone for domain: {smarter_settings.root_domain}: {additional_ns_records}"
            )
        )

        # 2. Api domain hosted zone verification. ie api.smarter.sh
        # ---------------------------------------------------------------------
        print("-" * 80)
        self.stdout.write(
            self.style.NOTICE(f"{log_prefix} (2) api domain DNS verification: {smarter_settings.api_domain}")
        )
        self.stdout.write(self.style.NOTICE(f"{log_prefix} verify DNS config for {smarter_settings.api_domain}"))
        api_domain_hosted_zone, created = aws_helper.route53.get_or_create_hosted_zone(
            domain_name=smarter_settings.api_domain
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created AWS Route53 hosted zone for customer api base domain: {smarter_settings.api_domain}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified AWS Route53 hosted zone for customer api base domain: {smarter_settings.api_domain}"
                )
            )
        print("-" * 80)

        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that an A record exists in root hosted zone {smarter_settings.root_domain} for {smarter_settings.api_domain}"
            )
        )
        api_domain_hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=api_domain_hosted_zone)
        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=api_domain_hosted_zone_id,
            record_name=smarter_settings.api_domain,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=600,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} created A record for api base domain {smarter_settings.api_domain}.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} verified A record for api base domain {smarter_settings.api_domain}.")
            )
        print("-" * 80)

        # verify that the NS records for the api domain are in the root domain hosted zone
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that NS records for {smarter_settings.api_domain} exist in {smarter_settings.root_domain} hosted zone."
            )
        )
        customer_api_domain_ns_records = self.get_ns_records_for_domain(domain=smarter_settings.api_domain)
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} NS records that should exist in {smarter_settings.root_domain} hosted zone for {smarter_settings.api_domain}: {customer_api_domain_ns_records}"
            )
        )

        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=root_domain_hosted_zone_id,
            record_name=smarter_settings.api_domain,
            record_type="NS",
            record_value=customer_api_domain_ns_records["ResourceRecords"],
            record_ttl=600,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created NS record for {smarter_settings.api_domain} in the root domain hosted zone."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified NS record for {smarter_settings.api_domain} in the root domain hosted zone."
                )
            )

        # 3. Platform domain hosted zone verification. ie platform.smarter.sh
        # ---------------------------------------------------------------------
        print("-" * 80)
        self.stdout.write(
            self.style.NOTICE(f"{log_prefix} (3) platform domain DNS verification: {smarter_settings.platform_domain}")
        )
        self.stdout.write(self.style.NOTICE(f"{log_prefix} verify DNS config for {smarter_settings.platform_domain}"))
        api_domain_hosted_zone, created = aws_helper.route53.get_or_create_hosted_zone(
            domain_name=smarter_settings.platform_domain
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created AWS Route53 hosted zone for root platform domain: {smarter_settings.platform_domain}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified AWS Route53 hosted zone for root platform domain: {smarter_settings.platform_domain}"
                )
            )
        print("-" * 80)

        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that an A record exists for hosted zone for {smarter_settings.platform_domain}"
            )
        )
        api_domain_hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=api_domain_hosted_zone)
        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=api_domain_hosted_zone_id,
            record_name=smarter_settings.platform_domain,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=600,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created A record for root platform domain {smarter_settings.platform_domain}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified A record for root platform domain {smarter_settings.platform_domain}."
                )
            )
        print("-" * 80)

        # verify that the NS records for the platform domain are in the root domain hosted zone
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that NS records for {smarter_settings.platform_domain} exist in {smarter_settings.root_domain} hosted zone."
            )
        )
        platform_domain_ns_records = self.get_ns_records_for_domain(domain=smarter_settings.platform_domain)
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} NS records that should exist in {smarter_settings.root_domain} hosted zone for {smarter_settings.platform_domain}: {platform_domain_ns_records}"
            )
        )

        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=root_domain_hosted_zone_id,
            record_name=smarter_settings.platform_domain,
            record_type="NS",
            record_value=customer_api_domain_ns_records["ResourceRecords"],
            record_ttl=600,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created NS record for {smarter_settings.platform_domain} in the root domain hosted zone {smarter_settings.root_domain}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified NS record for {smarter_settings.platform_domain} in the root domain hosted zone {smarter_settings.root_domain}."
                )
            )

        print("-" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                f"{log_prefix} verified platform level DNS infrastructure for {smarter_settings.root_domain}, {smarter_settings.platform_domain} and {smarter_settings.api_domain}"
            )
        )
        print("-" * 80)

    def verify(self, domain: str, parent_domain: str):
        """
        Verify the AWS Route53 hosted zone for the environment platform domain
        ie alpha.platform.smarter.sh, beta.platform.smarter.sh, etc.
        1. hosted zone for 'domain' should exist. if not, create it.
        2. NS records for 'domain' should exist in hosted zone of parent_domain. if not, create them
        3. environment hosted zone should contain A record alias to the AWS Classic Load Balancer.
        4. platform hosted zone should contain CNAME record for _acme-challenge pointing to 'domain'.
        """
        log_prefix = self.log_prefix + " - " + f"verify() - domain: {domain}, parent_domain: {parent_domain}"
        print("-" * 80)
        self.stdout.write(
            self.style.NOTICE(f"{log_prefix} verifying AWS Route53 DNS infrastructure for domain: {domain}")
        )
        print("-" * 80)

        domain = aws_helper.aws.domain_resolver(domain)
        parent_domain = aws_helper.aws.domain_resolver(parent_domain)
        parent_hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=parent_domain)

        # 1. Verify that the AWS Route53 hosted zone exists: ie alpha.platform.smarter.sh, beta.platform.smarter.sh, etc.
        # ---------------------------------------------------------------------
        environment_api_domain_hosted_zone_id, created = aws_helper.route53.get_or_create_hosted_zone(
            domain_name=domain
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created AWS Route53 hosted zone for domain: {domain}: {environment_api_domain_hosted_zone_id}"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"{log_prefix} verified hosted zone for domain: {domain}"))
        environment_api_domain_hosted_zone_id = aws_helper.route53.get_hosted_zone_id(
            hosted_zone=environment_api_domain_hosted_zone_id
        )
        print("-" * 80)

        # 2. Verify that the NS records for the domain exist in the parent domain's hosted zone
        # ---------------------------------------------------------------------
        ns_records = self.get_ns_records_for_domain(domain=domain)
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} NS records for {domain} that should exist in hosted zone for {parent_domain}: {ns_records}"
            )
        )

        ns_record, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=parent_hosted_zone_id,
            record_name=domain,
            record_type="NS",
            record_value=ns_records["ResourceRecords"],
            record_ttl=300,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} added NS Records for {domain} to hosted zone for {parent_domain}: {ns_record}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified NS Records for {domain} in hosted zone for {parent_domain}: {ns_record}"
                )
            )

        # 3. Verify that an A record exists for the domain hosted zone
        # ---------------------------------------------------------------------
        a_record = self.get_an_A_record()

        this_a_record, create = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=environment_api_domain_hosted_zone_id,
            record_name=domain,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=600,
        )
        if create:
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} created A record for domain {domain} hosted zone.: {this_a_record}")
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"{log_prefix} verified A record for domain {domain} hosted zone."))

        # 4. Verify that the CNAME record for _acme-challenge exists in the parent domain hosted zone
        # ---------------------------------------------------------------------
        acme_challenge_record, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=parent_hosted_zone_id,
            record_name=f"_acme-challenge.{domain}",
            record_type="CNAME",
            record_value=domain,
            record_ttl=300,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created CNAME record for _acme-challenge.{domain} in hosted zone for {parent_domain}: {acme_challenge_record}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified CNAME record for _acme-challenge.{domain} in hosted zone for {parent_domain}."
                )
            )

        print("-" * 80)
        self.stdout.write(
            self.style.SUCCESS(f"{log_prefix} verified AWS Route53 DNS infrastructure for domain: {domain}")
        )
        print("-" * 80)

    def handle(self, *args, **options):
        print("*" * 80)
        print(f"{self.log_prefix}")
        print("*" * 80)

        self.verify_base_dns_config()

        # for non-production environments, we need to verify the environment specific domains
        if smarter_settings.environment_api_domain != smarter_settings.api_domain:
            self.verify(domain=smarter_settings.environment_api_domain, parent_domain=smarter_settings.api_domain)
        if smarter_settings.environment_domain != smarter_settings.platform_domain:
            self.verify(domain=smarter_settings.environment_domain, parent_domain=smarter_settings.platform_domain)

        print("*" * 80)
        self.stdout.write(self.style.SUCCESS(f"{self.log_prefix} completed successfully."))
        print("*" * 80)
