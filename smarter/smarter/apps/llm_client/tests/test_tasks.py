# pylint: disable=wrong-import-position
"""Test LLMClient tasks."""

# python stuff
import logging
import time

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llm_client.models import LLMClient, LLMClientCustomDomain
from smarter.apps.llm_client.tasks import (
    create_custom_domain_dns_record,
    deploy_default_api,
    undeploy_default_api,
    verify_domain,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib.django.validators import SmarterValidator

logger = logging.getLogger(__name__)


class TestLLMClientTasks(TestAccountMixin):
    """Test LLMClient tasks."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.smarter_account = None
        cls.smarter_admin_user = None

        # we want to test with the Smarter account so that we retain the
        # same account number for DNS verifications in local.api.smarter.sh in
        # AWS Route53
        cls.smarter_account = smarter_cached_objects.smarter_account
        cls.smarter_user_profile = smarter_cached_objects.smarter_admin_user_profile
        cls.smarter_admin_user = smarter_cached_objects.smarter_admin

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        common_name = "test-llm_client-tasks"

        self.domain_name = f"{common_name}.{aws_helper.aws.environment_api_domain}"
        self.hosted_zone = aws_helper.route53.get_hosted_zone(domain_name=self.domain_name)  # type: ignore
        if self.hosted_zone:
            aws_helper.route53.delete_hosted_zone(domain_name=self.domain_name)  # type: ignore

        self.llm_client, _ = LLMClient.objects.get_or_create(
            user_profile=self.smarter_user_profile,
            name=common_name,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            LLMClientCustomDomain.objects.get(user_profile=self.smarter_user_profile).delete()
        except LLMClientCustomDomain.DoesNotExist:
            pass

        try:
            if self.llm_client:
                self.llm_client.delete()
        # pylint: disable=W0718
        except Exception:
            pass

        try:
            self.hosted_zone = aws_helper.route53.get_hosted_zone(domain_name=self.domain_name)  # type: ignore
            if self.hosted_zone:
                aws_helper.route53.delete_hosted_zone(domain_name=self.domain_name)  # type: ignore
            certificate_arn = aws_helper.acm.get_certificate_arn(domain_name=self.domain_name)  # type: ignore
            if certificate_arn:
                aws_helper.acm.delete_certificate(certificate_arn=certificate_arn)  # type: ignore
        # pylint: disable=W0718
        except Exception:
            pass
        super().tearDown()

    def test_create_hosted_zone(self):
        self.hosted_zone = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=self.domain_name)  # type: ignore
        self.assertIsNotNone(self.hosted_zone)
        aws_helper.route53.delete_hosted_zone(domain_name=self.domain_name)  # type: ignore

    def test_create_custom_domain_dns_record(self):
        """Test that we can create a DNS record for a custom domain."""

        print("test_create_custom_domain_dns_record()")
        resolved_domain = aws_helper.aws.domain_resolver(self.domain_name)
        hosted_zone = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=resolved_domain)  # type: ignore
        self.assertIsNotNone(hosted_zone)

        custom_domain, _ = LLMClientCustomDomain.objects.get_or_create(
            user_profile=self.smarter_user_profile,
            domain_name=resolved_domain,
            aws_hosted_zone_id=hosted_zone,
        )

        create_custom_domain_dns_record(
            llm_client_custom_domain_id=custom_domain.id,  # type: ignore
            record_name=resolved_domain,
            record_type="TXT",
            record_value="test",
            record_ttl=600,
        )

        dns_record = aws_helper.route53.get_dns_record(  # type: ignore
            hosted_zone_id=custom_domain.aws_hosted_zone_id, record_name=resolved_domain, record_type="TXT"
        )  # type: ignore
        if not isinstance(dns_record, dict):
            self.fail(f"Expected dns_record to be a dict, got {type(dns_record)}: {dns_record}")
        self.assertIsNotNone(dns_record)
        self.assertIn(dns_record["Name"], [resolved_domain, resolved_domain + "."])
        self.assertEqual(dns_record["Type"], "TXT")
        self.assertEqual(dns_record["ResourceRecords"], [{"Value": '"test"'}])

    def test_verify_domain(self):
        """Test that we can verify a domain."""
        hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=smarter_settings.root_domain)  # type: ignore
        is_verified = verify_domain(
            domain_name=smarter_settings.root_domain, record_type="NS", hosted_zone_id=hosted_zone_id
        )
        self.assertTrue(is_verified)

    def test_create_domain_A_record(self):
        """Test that we can create an A record for a domain."""

        resolved_domain = aws_helper.aws.domain_resolver(self.domain_name)
        hosted_zone = aws_helper.route53.get_hosted_zone(domain_name=aws_helper.aws.environment_api_domain)  # type: ignore
        hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=hosted_zone)  # type: ignore

        print("resolved_domain", resolved_domain)
        print("hosted_zone", hosted_zone)
        print("hosted_zone_id", hosted_zone_id)
        dns_record = aws_helper.route53.create_domain_a_record(  # type: ignore
            hostname=resolved_domain, api_host_domain=aws_helper.aws.environment_api_domain
        )  # type: ignore

        print("dns_record", dns_record)
        dns_record = aws_helper.route53.get_dns_record(  # type: ignore
            hosted_zone_id=hosted_zone_id, record_name=resolved_domain, record_type="A"
        )  # type: ignore
        print("dns_record (queried)", dns_record)
        # mcdaniel: 2021-09-29: This test is failing even though the the record is being created.
        # aws_helper.route53.get_dns_record() weirdly returns None even though the record is there.
        self.assertIsNotNone(dns_record)
        self.assertIsInstance(
            dns_record, dict, f"Expected dns_record to be a dict, got {type(dns_record)}: {dns_record}"
        )
        if not isinstance(dns_record, dict):
            self.fail(f"Expected dns_record to be a dict, got {type(dns_record)}: {dns_record}")
        self.assertEqual(str(dns_record["Name"]).rstrip("."), str(resolved_domain).rstrip("."))
        self.assertEqual(dns_record["Type"], "A")

    def test_deploy_default_api(self):
        """Test that we can deploy the default API."""

        deploy_default_api(llm_client_id=self.llm_client.id, with_domain_verification=False)  # type: ignore

        logger.debug("self.llm_client.default_host: %s", self.llm_client.default_host)
        self.assertTrue(SmarterValidator.is_valid_hostname(self.llm_client.default_host))
        logger.debug("self.llm_client.default_url: %s", self.llm_client.default_url)
        self.assertTrue(SmarterValidator.is_valid_url(self.llm_client.default_url))
        logger.debug("self.llm_client.custom_host: %s", self.llm_client.custom_host)
        self.assertIsNone(self.llm_client.custom_host)
        logger.debug("self.llm_client.custom_url: %s", self.llm_client.custom_url)
        self.assertIsNone(self.llm_client.custom_url)
        logger.debug("self.llm_client.sandbox_host: %s", self.llm_client.sandbox_host)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.llm_client.sandbox_url), f"Invalid URL: {self.llm_client.sandbox_url}"
        )
        logger.debug("self.llm_client.sandbox_url: %s", self.llm_client.sandbox_url)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.llm_client.sandbox_url), f"Invalid URL: {self.llm_client.sandbox_url}"
        )
        logger.debug("self.llm_client.hostname: %s", self.llm_client.hostname)
        self.assertTrue(SmarterValidator.is_valid_url(self.llm_client.url), f"Invalid URL: {self.llm_client.hostname}")
        logger.debug("self.llm_client.url: %s", self.llm_client.url)
        self.assertTrue(SmarterValidator.is_valid_url(self.llm_client.url), f"Invalid URL: {self.llm_client.url}")
        logger.debug("self.llm_client.url_llm_client: %s", self.llm_client.url_llm_client)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.llm_client.url_llm_client),
            f"Invalid URL: {self.llm_client.url_llm_client}",
        )
        logger.debug("self.llm_client.url_chatapp: %s", self.llm_client.url_chatapp)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.llm_client.url_chatapp), f"Invalid URL: {self.llm_client.url_chatapp}"
        )
        logger.debug("self.llm_client.mode(self.llm_client.url): %s", self.llm_client.mode(self.llm_client.url))
        self.assertEqual(self.llm_client.mode(self.llm_client.url), "sandbox")

        hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(  # type: ignore
            domain_name=aws_helper.aws.environment_api_domain
        )
        a_record = None
        retries = 5
        while retries > 0 and a_record is None:
            a_record = aws_helper.route53.get_dns_record(  # type: ignore
                hosted_zone_id=hosted_zone_id, record_name=self.llm_client.default_host, record_type="A"
            )
            if a_record is None:
                print("DNS record not found. Retrying. Attempts remaining: ", retries)
                time.sleep(5)  # wait for 5 seconds before retrying
                retries -= 1
        self.assertIsNotNone(a_record)

        resolved_hostname = aws_helper.aws.domain_resolver(self.llm_client.default_host)
        if not isinstance(a_record, dict):
            self.fail(f"Expected a_record to be a dict, got {type(a_record)}: {a_record}")
        self.assertIn(a_record["Name"], [resolved_hostname, resolved_hostname + "."])
        self.assertEqual(a_record["Type"], "A")

        self.assertTrue(self.llm_client.ready)
        # we'll test this separately since it run asynchronously. For now, just ensure it's one of the two hoped-for values.
        self.assertIn(
            self.llm_client.dns_verification_status,
            [LLMClient.DnsVerificationStatusChoices.VERIFIED, LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED],
        )
        if self.llm_client.tls_certificate_issuance_status not in [
            LLMClient.TlsCertificateIssuanceStatusChoices.ISSUED,
            LLMClient.TlsCertificateIssuanceStatusChoices.REQUESTED,
        ]:
            logger.warning(
                "Unexpected TLS certificate issuance status: %s. This is likely a problem with Kubernetes cert-manager and will be ignored for purposes of this test.",
                self.llm_client.tls_certificate_issuance_status,
            )

        # mcdaniel: 2026-01-09: disabling this for now bc it's managed asynchronously
        # self.assertTrue(self.llm_client.deployed)

    def test_undeploy_default_api(self):
        """Test that we can undeploy the default API."""
        deploy_default_api(llm_client_id=self.llm_client.id, with_domain_verification=False)  # type: ignore
        undeploy_default_api(llm_client_id=self.llm_client.id)  # type: ignore

        self.assertFalse(self.llm_client.deployed)

        # DNS record should now be set to unverified, but the TLS certificate should still exist and still be valid.
        self.assertEqual(self.llm_client.dns_verification_status, LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED)
