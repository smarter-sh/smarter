"""This module verifies AWS Route53 DNS resources required by the Smarter platform."""

from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.aws.route53 import AWSRoute53
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Management command for verifying AWS Route53 DNS resources required by the
    Smarter platform. The general structure of DNS in AWS Route53 for a Smarter
    installation is as follows:

    - example.com
      The root domain with hosted zone in AWS Route53 in the AWS account. This
      should have been created independently of this code base. This command
      will only verify that the Hosted Zone for the root domain exists. If
      it is missing then the command will fail.
    - [platform].example.com
      The platform domain with hosted zone in AWS Route53 in the AWS account
      and NS records in the root domain hosted zone delegating to it.
      This should have been created as part of the Terraform infrastructure
      provisioning for the platform. But if not, this command will create it
      and add the necessary NS records to the root domain hosted zone.
    - api.[platform].example.com
      The API domain for the platform with hosted zone in AWS Route53 in the
      AWS account and NS records in the platform domain hosted zone delegating to it.
      This should have been created as part of the Terraform infrastructure
      provisioning for the platform. But if not, this command will create it and
      add the necessary NS records to the platform domain hosted zone.
    - local.example.com
      The local proxy domain with hosted zone in AWS Route53 in the AWS account
      and NS records in the root domain hosted zone delegating to it.
    - api.local.example.com
      The local API proxy domain with hosted zone in AWS Route53 in the AWS account
      and NS records in the local proxy domain hosted zone delegating to it.
    - [alpha].[platform].example.com
      A non-production platform domain with hosted zone in AWS Route53 in the AWS account
      and NS records in the root domain hosted zone delegating to it.
    - [alpha].api.[platform].example.com
      A non-production API domain with hosted zone in AWS Route53 in the AWS
      account and NS records in the platform domain hosted zone delegating to it.

    **Usage:**

    This command is intended to be run during deployment, or in running installations as part of DNS trouble shooting.
    It is useful for administrators and DevOps engineers as an automated tool to validate and/or
    repair DNS infrastructure in AWS Route53 for the Smarter platform.

    **Error Handling and Output:**

    - Raises clear exceptions and outputs descriptive error messages if any required DNS resource is missing or misconfigured.
    - Fails gracefully if AWS is not configured, or if the Route53 helper is not initialized.
    - Reports the status of each verification and creation step, making it easy to identify and resolve issues.

    .. seealso::

        :py:class:`smarter.common.helpers.aws.route53.AWSRoute53` - AWS Route53 helper class used for DNS operations.
        :py:data:`smarter.common.helpers.aws_helpers.aws_helper` - AWS helper module for initializing AWS services.
    """

    log_prefix = formatted_text(f"{__name__}.Command()")

    def get_any_A_record(self) -> dict:
        """
        A records all resolve to the same AWS Classic Load Balancer.
        This is a simple traversal method to look for and retrieve an A record
        from the AWS Route53 hosted zone for any of the existing domains.
        """
        log_prefix = self.log_prefix + ".get_any_A_record()"
        if not isinstance(aws_helper.route53, AWSRoute53):
            raise SmarterConfigurationError(f"{log_prefix} AWS Route53 helper is not initialized. Cannot proceed.")

        for some_domain in smarter_settings.all_domains:
            self.stdout.write(self.style.NOTICE(f"looking for an A record in {some_domain}..."))
            a_record = aws_helper.route53.get_environment_A_record(domain=some_domain)
            if a_record:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{log_prefix} found an A record in the hosted zone for domain: {a_record['Name']}"
                    )
                )
                return a_record

        raise SmarterConfigurationError(
            f"{log_prefix} Checked the following domains: {smarter_settings.all_domains} but couldn't find an A record to propagate. Cannot proceed."
        )

    def verify_domain_delegated_from_parent(self, child_domain: str, parent_domain: str, a_record: dict):
        """
        Verify the AWS Route53 hosted zone for the child domain.
        example: api.example.com

        - hosted zone for child_domain should exist.
        - hosted zone should contain A record alias to the AWS Classic Load Balancer.
        - NS records for the child_domain hosted zone should exist in the parent_domain hosted zone.

        :param child_domain: the child domain to verify. example: api.example.com
        :type child_domain: str
        :param parent_domain: the parent domain that should have NS records delegating to the child domain. example: example.com
        :type parent_domain: str
        :param a_record: an A record to use for verification and creation if needed. This should be an A record alias to the AWS Classic Load Balancer that is serving traffic for the Sm
        :type a_record: dict

        :return: None
        """

        log_prefix = self.log_prefix + ".verify_domain_delegated_from_parent()"
        self.stdout.write(f"{log_prefix} - {child_domain} delegated from parent domain: {parent_domain}")

        parent_domain_hosted_zone_id, _ = aws_helper.route53.get_or_create_hosted_zone(domain_name=parent_domain)
        parent_domain_hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=parent_domain_hosted_zone_id)

        self.stdout.write(self.style.NOTICE("-" * 80))
        self.stdout.write(self.style.NOTICE(f"{log_prefix} {child_domain} DNS verification"))

        root_api_domain_hosted_zone, created = aws_helper.route53.get_or_create_hosted_zone(domain_name=child_domain)
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} created AWS Route53 hosted zone for child domain: {child_domain}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} verified AWS Route53 hosted zone for child domain: {child_domain}")
            )

        self.stdout.write(
            self.style.NOTICE(f"{log_prefix} verify that an A record exists in child hosted zone {child_domain}")
        )
        child_domain_hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=root_api_domain_hosted_zone)
        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=child_domain_hosted_zone_id,
            record_name=child_domain,
            record_type="A",
            record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
            record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
            record_ttl=600,
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"{log_prefix} created A record for api base domain {child_domain}."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{log_prefix} verified A record for api base domain {child_domain}."))

        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verify that NS records for {child_domain} exist in {parent_domain} hosted zone."
            )
        )
        child_domain_ns_records = aws_helper.route53.get_ns_records_for_domain(domain=child_domain)
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} {child_domain} NS records that should exist in {parent_domain} hosted zone: {child_domain_ns_records}"
            )
        )

        _, created = aws_helper.route53.get_or_create_dns_record(
            hosted_zone_id=parent_domain_hosted_zone_id,
            record_name=child_domain,
            record_type="NS",
            record_value=child_domain_ns_records["ResourceRecords"],
            record_ttl=600,
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} created NS record for {child_domain} in {parent_domain}.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} verified NS record for {child_domain} in {parent_domain}.")
            )

    def verify_root_domain_dns_config(self):
        """
        Verify the AWS Route53 hosted zone for the root domain. ie example.com
        - hosted zone for root domain should exist.
        - hosted zone should contain A record alias to the AWS Classic Load Balancer.
        - hosted zone should contain NS records for the root domain (as is expected for any Hosted Zone).

        :return: None
        """
        log_prefix = self.log_prefix + ".verify_root_domain_dns_config()"
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

    def verify_base_dns_config(self) -> list[str]:
        """
        Verify the AWS Route53 hosted zones for domains associated with the
        Smarter platform. This includes any of the following domains depending
        on the configuration and the environment in which this command is
        being run:

        - example.com (root domain)
        - platform.example.com (platform domain)
        - api.platform.example.com (api domain)
        - local.example.com (local proxy domain)
        - api.local.example.com (local api proxy domain)
        - alpha.platform.example.com (non-production platform domain)
        - alpha.api.platform.example.com (non-production api domain)

        :return: list of verified domains
        :rtype: list[str]
        """
        if not isinstance(aws_helper.route53, AWSRoute53):
            raise SmarterConfigurationError(f"{self.log_prefix} AWS Route53 helper is not initialized. Cannot proceed.")

        log_prefix = self.log_prefix + ".verify_base_dns_config()"
        verified_domains = []
        self.stdout.write(self.style.NOTICE("-" * 80))
        self.stdout.write(
            self.style.NOTICE(
                f"{log_prefix} verifying DNS configuration for {smarter_settings.root_domain}, {smarter_settings.root_platform_domain} and {smarter_settings.root_api_domain}"
            )
        )
        self.stdout.write(self.style.NOTICE("-" * 80))

        # 1. Root domain hosted zone verification, ie example.com. This needs to exist in AWS Route53
        #    independent of this code base.
        # ---------------------------------------------------------------------
        self.verify_root_domain_dns_config()
        verified_domains.append(smarter_settings.root_domain)
        a_record = aws_helper.route53.get_environment_A_record(domain=smarter_settings.root_domain)
        if not a_record:
            raise SmarterConfigurationError(
                f"{log_prefix} Couldn't find an A record in the root domain: "
                f"{smarter_settings.root_domain}. Expected to find an 'A' record alias to an AWS Route53 "
                "classic balancer. Cannot proceed."
            )

        # ---------------------------------------------------------------------
        # 2. platform domain hosted zone verification. ie platform.example.com
        # ---------------------------------------------------------------------
        if smarter_settings.environment != SmarterEnvironments.LOCAL:
            self.verify_domain_delegated_from_parent(
                child_domain=smarter_settings.root_platform_domain,
                parent_domain=smarter_settings.root_domain,
                a_record=a_record,
            )
            verified_domains.append(smarter_settings.root_platform_domain)
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f"{log_prefix} skipping hosted zone verification for {smarter_settings.root_platform_domain} because environment is {SmarterEnvironments.LOCAL}."
                )
            )

        # ---------------------------------------------------------------------
        # 3. Local proxy domain hosted zone verification. ie local.example.com
        # ---------------------------------------------------------------------
        self.verify_domain_delegated_from_parent(
            child_domain=smarter_settings.root_proxy_domain,
            parent_domain=smarter_settings.root_domain,
            a_record=a_record,
        )
        verified_domains.append(smarter_settings.root_proxy_domain)

        # ---------------------------------------------------------------------
        # 4. Local api proxy domain hosted zone verification. ie api.local.example.com
        # ---------------------------------------------------------------------
        self.verify_domain_delegated_from_parent(
            child_domain=smarter_settings.proxy_api_domain,
            parent_domain=smarter_settings.root_proxy_domain,
            a_record=a_record,
        )
        verified_domains.append(smarter_settings.proxy_api_domain)

        if smarter_settings.environment == SmarterEnvironments.LOCAL:
            return verified_domains

        # ---------------------------------------------------------------------
        # 5. Api domain hosted zone verification. ie api.example.com
        # ---------------------------------------------------------------------
        if smarter_settings.environment != SmarterEnvironments.LOCAL:
            self.verify_domain_delegated_from_parent(
                child_domain=smarter_settings.root_api_domain,
                parent_domain=smarter_settings.root_platform_domain,
                a_record=a_record,
            )
            verified_domains.append(smarter_settings.root_api_domain)
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f"{log_prefix} skipping hosted zone verification for {smarter_settings.root_api_domain} because environment is {SmarterEnvironments.LOCAL}."
                )
            )

        # ---------------------------------------------------------------------
        # 6. non-production platform domain hosted zone verification.
        # ie alpha.platform.example.com
        # ---------------------------------------------------------------------
        if smarter_settings.environment_api_domain != smarter_settings.root_api_domain:
            self.verify_domain_delegated_from_parent(
                child_domain=smarter_settings.environment_platform_domain,
                parent_domain=smarter_settings.root_platform_domain,
                a_record=a_record,
            )
            verified_domains.append(smarter_settings.environment_platform_domain)

        # ---------------------------------------------------------------------
        # 7. Environment specific domain hosted zone verification.
        # ie alpha.api.platform.example.com
        # ---------------------------------------------------------------------
        if smarter_settings.environment_api_domain != smarter_settings.root_api_domain:
            self.verify_domain_delegated_from_parent(
                child_domain=smarter_settings.environment_api_domain,
                parent_domain=smarter_settings.root_api_domain,
                a_record=a_record,
            )
            verified_domains.append(smarter_settings.environment_api_domain)

        return verified_domains

    def handle(self, *args, **options):
        """Verify DNS configuration."""
        self.handle_begin()

        if not smarter_settings.aws_is_configured:
            # fail gracefully if AWS is not configured
            self.handle_completed_failure(msg=f"{self.log_prefix} AWS is not configured. Cannot proceed.")
            return

        try:
            verified_domains = self.verify_base_dns_config()
        except SmarterConfigurationError as exc:
            self.handle_completed_failure(exc)
            return

        if len(verified_domains) > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{self.log_prefix} verified platform level DNS infrastructure for the following domains: {', '.join(verified_domains)}"
                )
            )

        self.handle_completed_success()
