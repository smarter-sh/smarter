"""A utility class for introspecting AWS infrastructure."""

import logging

# python stuff
import time
from typing import Optional

from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

# our stuff
from .aws import AWSBase, SmarterAWSException
from .exceptions import AWSACMVerificationFailed


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.TASK_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class AWSCertificateManager(AWSBase):
    """AWS Certificate Manager helper class."""

    _client = None
    _route53 = None

    @property
    def client(self):
        """Return the AWS ACM client"""
        if self._client:
            return self._client
        if not self.aws_session:
            raise SmarterAWSException("AWS session is not initialized.")
        self._client = self.aws_session.client("acm")
        return self._client

    @property
    def route53(self):
        """Return the AWS Route53 helper."""
        if self._route53 is None:
            # pylint: disable=import-outside-toplevel
            from .route53 import AWSRoute53

            self._route53 = AWSRoute53()
        return self._route53

    def get_certificate_arn(self, domain_name) -> Optional[str]:
        """Return the certificate ARN."""
        response = self.client.list_certificates()
        for certificate in response["CertificateSummaryList"]:
            if certificate["DomainName"] == domain_name:
                return certificate["CertificateArn"]
        return None

    def get_certificate_status(self, certificate_arn: str) -> dict:
        """
        Return the certificate status
        see example return in ./data/aws/certificate_detail.json
        """
        sleep_interval = 5
        max_attempts = int(600 / sleep_interval)
        attempts = 0

        while True:
            try:
                certificate_detail = self.client.describe_certificate(CertificateArn=certificate_arn)

                # look for a DNS ResourceRecord in the DomainValidationOptions for the Certificate
                certificate = certificate_detail.get("Certificate")
                if certificate:
                    domain_validation_options = certificate.get("DomainValidationOptions")
                    if domain_validation_options:
                        resource_record = domain_validation_options[0].get("ResourceRecord")
                        if resource_record:
                            logger.info("Found DNS records for ACM certificate ARN: %s", certificate_arn)
                            return certificate_detail
                logger.info("Waiting for DNS records to be generated for ACM certificate ARN: %s", certificate_arn)
                attempts += 1
                time.sleep(sleep_interval)
            except self.client.exceptions.ResourceNotFoundException as e:
                attempts += 1
                if attempts >= max_attempts:
                    raise e(f"Failed to get certificate details for AWS ACM certificate ARN {certificate_arn}") from e
                # Wait for a while before describing the certificate
                # as it can take a few seconds for ACM to generate the DNS records
                time.sleep(sleep_interval)

    def get_or_create_certificate(self, domain_name) -> str:
        """Return the certificate ARN."""
        # look for existing certificate
        certificate_arn = self.get_certificate_arn(domain_name)
        if not certificate_arn:
            # create a new certificate since we didn't find an existing one
            response = self.client.request_certificate(
                DomainName=domain_name,
                ValidationMethod="DNS",
                SubjectAlternativeNames=[f"*.{domain_name}"],
            )
            certificate_arn = response["CertificateArn"]

        return certificate_arn

    def get_or_create_certificate_dns_record(self, certificate_arn: str) -> dict:
        """
        Get or create the DNS verification record for the certificate.

        """
        # get the certificate details
        certificate_detail = self.get_certificate_status(certificate_arn=certificate_arn)

        dns_records = certificate_detail["Certificate"]["DomainValidationOptions"]
        domain_name = dns_records[0]["DomainName"]
        resource_record = dns_records[0]["ResourceRecord"]
        dns_record_name = resource_record["Name"]
        dns_record_type = resource_record["Type"]
        dns_record_value = resource_record["Value"]
        hosted_zone, _ = self.route53.get_or_create_hosted_zone(domain_name)
        hosted_zone_id = self.route53.get_hosted_zone_id(hosted_zone)

        dns_record, _ = self.route53.get_or_create_dns_record(
            hosted_zone_id=hosted_zone_id,
            record_name=dns_record_name,
            record_type=dns_record_type,
            record_value=dns_record_value,
            record_ttl=300,
        )

        return dns_record

    def certificate_is_verified(self, certificate_arn: str) -> bool:
        """Return whether the certificate is verified."""
        certificate_detail = self.get_certificate_status(certificate_arn=certificate_arn)
        return certificate_detail["Certificate"]["Status"] == "SUCCESS"

    def verify_certificate(self, certificate_arn: str) -> bool:
        sleep_interval = 30
        max_attempts = int(600 / sleep_interval)
        attempts = 0
        if self.certificate_is_verified(certificate_arn):
            return True

        while not self.certificate_is_verified(certificate_arn=certificate_arn):
            attempts += 1
            if attempts >= max_attempts:
                try:
                    raise AWSACMVerificationFailed(f"Failed to verify ACM certificate ARN {certificate_arn}")
                except AWSACMVerificationFailed as e:
                    logger.exception(e)
                    return False
            time.sleep(sleep_interval)
        return True

    def delete_certificate(self, certificate_arn: str):
        """Delete the certificate."""
        try:
            self.client.delete_certificate(CertificateArn=certificate_arn)
        except self.client.exceptions.ResourceNotFoundException:
            pass
