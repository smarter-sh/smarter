"""This module is used to initialize the environment."""

from django.core.management.base import BaseCommand

from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.aws_helpers import aws_helper


# pylint: disable=E1101
class Command(BaseCommand):
    """
    Verify AWS Route53 resources.
    - root:     example.com
    - api:      api.example.com, alpha.api.example.com, beta.api.example.com, etc.
    - platform: platform.example.com, alpha.platform.example.com, beta.platform.example.com, etc.
    """

    log_prefix = "manage.py verify_dns_configuration()"

    def get_any_A_record(self) -> dict:
        """
        A records all resolve to the same AWS Classic Load Balancer.
        This is a simple traversal method to look for and retrieve an A record
        from the AWS Route53 hosted zone for any of the existing domains.
        """
        for some_domain in smarter_settings.all_domains:
            print(f"looking for an A record in {some_domain}...")
            a_record = aws_helper.route53.get_environment_A_record(domain=some_domain)
            if a_record:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"get_any_A_record() found an A record in the hosted zone for domain: {a_record['Name']}"
                    )
                )
                return a_record

        raise SmarterConfigurationError(
            f"get_any_A_record() Checked the following domains: {smarter_settings.all_domains} but couldn't find an A record to propagate. Cannot proceed."
        )

    # pylint: disable=R0912,R0915
    def verify_base_dns_config(self):
        """
        Verify the AWS Route53 hosted zones for the root domain, api domain and platform domain.
        """

        log_prefix = self.log_prefix + " - " + "verify_base_dns_config()"
        print("-" * 80)
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verifying DNS configuration for {smarter_settings.root_domain}, {smarter_settings.root_platform_domain} and {smarter_settings.root_api_domain}"
            )
        )
        print("-" * 80)

        # 1. Root domain hosted zone verification, ie example.com. This needs to exist in AWS Route53
        #    independent of this code base.
        #
        #    Verify the AWS Route53 hosted zone for the root domain. ie example.com
        #     - hosted zone for root domain should exist.
        #     - hosted zone should contain A record alias to the AWS Classic Load Balancer.
        #     - hosted zone should contain NS records for the root domain (as is expected for any Hosted Zone).
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
            raise SmarterConfigurationError(
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
            raise SmarterConfigurationError(
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
        # we're expecting three sets of NS records, for example.com, api.example.com, platform.example.com.
        if not isinstance(ns_records, list):
            raise SmarterConfigurationError(
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

        # 2. Api domain hosted zone verification. ie api.example.com
        #    Verify the AWS Route53 hosted zone for the root api domain. example: api.example.com
        #     - hosted zone for 'api.example.com' should exist.
        #     - hosted zone should contain A record alias to the AWS Classic Load Balancer.
        #     - NS records for this hosted zone should exist in the root domain hosted zone.
        # ---------------------------------------------------------------------
        print("-" * 80)
        self.stdout.write(
            self.style.NOTICE(f"{log_prefix} (2) api domain DNS verification: {smarter_settings.root_api_domain}")
        )
        self.stdout.write(self.style.NOTICE(f"{log_prefix} verify DNS config for {smarter_settings.root_api_domain}"))
        root_api_domain_hosted_zone, created = aws_helper.route53.get_or_create_hosted_zone(
            domain_name=smarter_settings.root_api_domain
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created AWS Route53 hosted zone for root api domain: {smarter_settings.root_api_domain}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified AWS Route53 hosted zone for root api domain: {smarter_settings.root_api_domain}"
                )
            )
        print("-" * 80)

        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that an A record exists in root api hosted zone {smarter_settings.root_api_domain}"
            )
        )
        root_api_domain_hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=root_api_domain_hosted_zone)
        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=root_api_domain_hosted_zone_id,
            record_name=smarter_settings.root_api_domain,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=600,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created A record for api base domain {smarter_settings.root_api_domain}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified A record for api base domain {smarter_settings.root_api_domain}."
                )
            )
        print("-" * 80)

        # verify that the NS records for the root api domain are in the root domain hosted zone
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that NS records for {smarter_settings.root_api_domain} exist in {smarter_settings.root_domain} hosted zone."
            )
        )
        customer_api_domain_ns_records = aws_helper.route53.get_ns_records_for_domain(
            domain=smarter_settings.root_api_domain
        )
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} NS records that should exist in {smarter_settings.root_domain} hosted zone for {smarter_settings.root_api_domain}: {customer_api_domain_ns_records}"
            )
        )

        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=root_domain_hosted_zone_id,
            record_name=smarter_settings.root_api_domain,
            record_type="NS",
            record_value=customer_api_domain_ns_records["ResourceRecords"],
            record_ttl=600,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created NS record for {smarter_settings.root_api_domain} in the root domain hosted zone."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified NS record for {smarter_settings.root_api_domain} in the root domain hosted zone."
                )
            )

        # 3. root platform domain hosted zone verification. ie platform.example.com
        #    Verify the AWS Route53 hosted zone for the root platform domain. ie platform.example.com
        #     - hosted zone for the root platform domain should exist.
        #     - hosted zone should contain A record alias to the AWS Classic Load Balancer.
        #     - NS records for this hosted zone should exist in the root domain hosted zone.
        # ---------------------------------------------------------------------
        print("-" * 80)
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} (3) root platform domain DNS verification: {smarter_settings.root_platform_domain}"
            )
        )
        self.stdout.write(
            self.style.NOTICE(f"{log_prefix} verify DNS config for {smarter_settings.root_platform_domain}")
        )
        root_platform_domain_hosted_zone, created = aws_helper.route53.get_or_create_hosted_zone(
            domain_name=smarter_settings.root_platform_domain
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created AWS Route53 hosted zone for root platform domain: {smarter_settings.root_platform_domain}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified AWS Route53 hosted zone for root platform domain: {smarter_settings.root_platform_domain}"
                )
            )
        print("-" * 80)

        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that an A record exists in hosted zone for {smarter_settings.root_platform_domain}"
            )
        )
        root_platform_domain_hosted_zone_id = aws_helper.route53.get_hosted_zone_id(
            hosted_zone=root_platform_domain_hosted_zone
        )
        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=root_platform_domain_hosted_zone_id,
            record_name=smarter_settings.root_platform_domain,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=600,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created A record for root platform domain {smarter_settings.root_platform_domain}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified A record for root platform domain {smarter_settings.root_platform_domain}."
                )
            )
        print("-" * 80)

        # verify that the NS records for the platform domain are in the root domain hosted zone
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that NS records for {smarter_settings.root_platform_domain} exist in {smarter_settings.root_domain} hosted zone."
            )
        )
        root_platform_domain_ns_records = aws_helper.route53.get_ns_records_for_domain(
            domain=smarter_settings.root_platform_domain
        )
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} NS records that should exist in {smarter_settings.root_domain} hosted zone for {smarter_settings.root_platform_domain}: {root_platform_domain_ns_records}"
            )
        )

        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=root_platform_domain_hosted_zone_id,
            record_name=smarter_settings.root_platform_domain,
            record_type="NS",
            record_value=customer_api_domain_ns_records["ResourceRecords"],
            record_ttl=600,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created NS record for {smarter_settings.root_platform_domain} in the root domain hosted zone {smarter_settings.root_domain}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified NS record for {smarter_settings.root_platform_domain} in the root domain hosted zone {smarter_settings.root_domain}."
                )
            )

        print("-" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                f"{log_prefix} verified platform level DNS infrastructure for {smarter_settings.root_domain}, {smarter_settings.root_platform_domain} and {smarter_settings.root_api_domain}"
            )
        )
        print("-" * 80)

    def verify(self, domain: str):
        """
        Verify the AWS Route53 hosted zone for the environment platform domain
        ie alpha.platform.example.com, beta.platform.example.com, etc.
        1. hosted zone for 'domain' should exist. if not, create it.
        2. NS records for 'domain' should exist in hosted zone of parent_domain. if not, create them
        3. environment hosted zone should contain A record alias to the AWS Classic Load Balancer. If not, create it.
        """

        def get_parent_domain(domain: str) -> str:
            """
            Given a domain like 'alpha.platform.example.com', return its parent domain 'platform.example.com'.
            """
            domain_no_port = domain.split(":")[0].strip(".")
            parts = domain_no_port.split(".")
            if len(parts) < 3:
                # For localhost or similar, just return the domain without port
                return domain_no_port
            parent_domain = ".".join(parts[1:])
            return aws_helper.aws.domain_resolver(parent_domain)

        resolved_domain = aws_helper.aws.domain_resolver(domain)
        parent_domain = get_parent_domain(resolved_domain)

        log_prefix = (
            self.log_prefix
            + " - "
            + f"verify() - domain: {domain}, resolved domain: {resolved_domain}, parent_domain: {parent_domain}"
        )
        print("-" * 80)
        self.stdout.write(
            self.style.NOTICE(f"{log_prefix} verifying AWS Route53 DNS infrastructure for domain: {resolved_domain}")
        )
        print("-" * 80)

        # 1. Verify that the AWS Route53 hosted zone exists for the environment platform
        #    example: alpha.platform.example.com, beta.platform.example.com, etc.
        # ---------------------------------------------------------------------
        _, created = aws_helper.route53.get_or_create_hosted_zone(domain_name=resolved_domain)
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created AWS Route53 hosted zone for resolved_domain: {resolved_domain}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} verified hosted zone for resolved_domain: {resolved_domain}")
            )

        domain_hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=resolved_domain)

        print("-" * 80)

        # 2. Verify that the NS records for the resolved_domain exist in the parent resolved_domain's hosted zone
        # ---------------------------------------------------------------------
        domain_ns_records = aws_helper.route53.get_ns_records_for_domain(domain=resolved_domain)
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} NS records for {resolved_domain} exist in the hosted zone for {parent_domain}. HostedZoneID: {domain_hosted_zone_id} NS records: {domain_ns_records}"
            )
        )

        parent_hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=parent_domain)
        ns_record, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=parent_hosted_zone_id,
            record_name=resolved_domain,
            record_type="NS",
            record_value=domain_ns_records["ResourceRecords"],
            record_ttl=300,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} added NS Records for {resolved_domain} to hosted zone for {parent_domain}: {ns_record}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} verified NS Records for {resolved_domain} in hosted zone for {parent_domain}: {ns_record}"
                )
            )

        # 3. Verify that an A record exists for the resolved_domain in its environment hosted zone
        # ---------------------------------------------------------------------
        a_record = self.get_any_A_record()

        domain_a_record, create = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=domain_hosted_zone_id,
            record_name=resolved_domain,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=600,
        )
        if create:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{log_prefix} created A record for domain {resolved_domain} hosted zone.: {domain_a_record}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} verified A record for domain {resolved_domain} in hosted zone.")
            )

        print("-" * 80)
        self.stdout.write(
            self.style.SUCCESS(f"{log_prefix} verified AWS Route53 DNS infrastructure for domain: {resolved_domain}")
        )
        print("-" * 80)

    def handle(self, *args, **options):
        print("*" * 80)
        print(f"{self.log_prefix}")
        print("*" * 80)

        self.verify_base_dns_config()

        # for non-production environments, we need to verify the environment specific domains
        if smarter_settings.environment_api_domain != smarter_settings.root_api_domain:
            # example: domain=alpha.api.example.com
            self.verify(domain=smarter_settings.environment_api_domain)
        if smarter_settings.environment_platform_domain != smarter_settings.root_platform_domain:
            # example: domain=alpha.platform.example.com
            self.verify(domain=smarter_settings.environment_platform_domain)

        print("*" * 80)
        self.stdout.write(self.style.SUCCESS(f"{self.log_prefix} completed successfully."))
        print("*" * 80)
