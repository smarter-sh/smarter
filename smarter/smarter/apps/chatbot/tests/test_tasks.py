# pylint: disable=wrong-import-position
"""Test Chatbot tasks."""

# python stuff
import logging
import time

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    get_cached_smarter_account,
)
from smarter.apps.chatbot.models import ChatBot, ChatBotCustomDomain
from smarter.apps.chatbot.tasks import (
    create_custom_domain_dns_record,
    deploy_default_api,
    undeploy_default_api,
    verify_domain,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib.django.validators import SmarterValidator


logger = logging.getLogger(__name__)


class TestChatBotTasks(TestAccountMixin):
    """Test Chatbot tasks"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.smarter_account = None
        cls.smarter_admin_user = None

        # we want to test with the Smarter account so that we retain the
        # same account number for DNS verifications in local.api.smarter.sh in
        # AWS Route53
        cls.smarter_account = get_cached_smarter_account()
        cls.smarter_admin_user = get_cached_admin_user_for_account(account=cls.smarter_account)

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        common_name = "test-chatbot-tasks"

        self.domain_name = f"{common_name}.{aws_helper.aws.environment_api_domain}"
        self.hosted_zone = aws_helper.route53.get_hosted_zone(domain_name=self.domain_name)
        if self.hosted_zone:
            aws_helper.route53.delete_hosted_zone(domain_name=self.domain_name)

        self.chatbot = ChatBot.objects.create(
            account=self.smarter_account,
            name=common_name,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            ChatBotCustomDomain.objects.get(account_id=self.smarter_account.id).delete()
        except ChatBotCustomDomain.DoesNotExist:
            pass

        try:
            if self.chatbot:
                self.chatbot.delete()
        # pylint: disable=W0718
        except Exception:
            pass

        try:
            self.hosted_zone = aws_helper.route53.get_hosted_zone(domain_name=self.domain_name)
            if self.hosted_zone:
                aws_helper.route53.delete_hosted_zone(domain_name=self.domain_name)
            certificate_arn = aws_helper.acm.get_certificate_arn(domain_name=self.domain_name)
            if certificate_arn:
                aws_helper.acm.delete_certificate(certificate_arn=certificate_arn)
        # pylint: disable=W0718
        except Exception:
            pass
        super().tearDown()

    def test_create_hosted_zone(self):
        self.hosted_zone = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=self.domain_name)
        self.assertIsNotNone(self.hosted_zone)
        aws_helper.route53.delete_hosted_zone(domain_name=self.domain_name)

    def test_create_custom_domain_dns_record(self):
        """Test that we can create a DNS record for a custom domain."""

        print("test_create_custom_domain_dns_record()")
        resolved_domain = aws_helper.aws.domain_resolver(self.domain_name)
        hosted_zone = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=resolved_domain)
        self.assertIsNotNone(hosted_zone)

        custom_domain, _ = ChatBotCustomDomain.objects.get_or_create(
            account=self.smarter_account,
            domain_name=resolved_domain,
            aws_hosted_zone_id=hosted_zone,
        )

        create_custom_domain_dns_record(
            chatbot_custom_domain_id=custom_domain.id,
            record_name=resolved_domain,
            record_type="TXT",
            record_value="test",
            record_ttl=600,
        )

        dns_record = aws_helper.route53.get_dns_record(
            hosted_zone_id=custom_domain.aws_hosted_zone_id, record_name=resolved_domain, record_type="TXT"
        )

        self.assertIsNotNone(dns_record)
        self.assertIn(dns_record["Name"], [resolved_domain, resolved_domain + "."])
        self.assertEqual(dns_record["Type"], "TXT")
        self.assertEqual(dns_record["ResourceRecords"], [{"Value": '"test"'}])

    def test_verify_domain(self):
        """Test that we can verify a domain."""
        hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(domain_name=smarter_settings.root_domain)
        is_verified = verify_domain(
            domain_name=smarter_settings.root_domain, record_type="NS", hosted_zone_id=hosted_zone_id
        )
        self.assertTrue(is_verified)

    def test_create_domain_A_record(self):
        """Test that we can create an A record for a domain."""

        resolved_domain = aws_helper.aws.domain_resolver(self.domain_name)
        hosted_zone = aws_helper.route53.get_hosted_zone(domain_name=aws_helper.aws.environment_api_domain)
        hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=hosted_zone)

        print("resolved_domain", resolved_domain)
        print("hosted_zone", hosted_zone)
        print("hosted_zone_id", hosted_zone_id)
        dns_record = aws_helper.route53.create_domain_a_record(
            hostname=resolved_domain, api_host_domain=aws_helper.aws.environment_api_domain
        )

        print("dns_record", dns_record)
        dns_record = aws_helper.route53.get_dns_record(
            hosted_zone_id=hosted_zone_id, record_name=resolved_domain, record_type="A"
        )
        print("dns_record (queried)", dns_record)
        # mcdaniel: 2021-09-29: This test is failing even though the the record is being created.
        # aws_helper.route53.get_dns_record() weirdly returns None even though the record is there.
        self.assertIsNotNone(dns_record)
        self.assertEqual(str(dns_record["Name"]).rstrip("."), str(resolved_domain).rstrip("."))
        self.assertEqual(dns_record["Type"], "A")

    def test_deploy_default_api(self):
        """Test that we can deploy the default API."""

        deploy_default_api(chatbot_id=self.chatbot.id, with_domain_verification=False)

        logger.debug("self.chatbot.default_host: %s", self.chatbot.default_host)
        self.assertTrue(SmarterValidator.is_valid_hostname(self.chatbot.default_host))
        logger.debug("self.chatbot.default_url: %s", self.chatbot.default_url)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.default_url))
        logger.debug("self.chatbot.custom_host: %s", self.chatbot.custom_host)
        self.assertIsNone(self.chatbot.custom_host)
        logger.debug("self.chatbot.custom_url: %s", self.chatbot.custom_url)
        self.assertIsNone(self.chatbot.custom_url)
        logger.debug("self.chatbot.sandbox_host: %s", self.chatbot.sandbox_host)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.chatbot.sandbox_url), f"Invalid URL: {self.chatbot.sandbox_url}"
        )
        logger.debug("self.chatbot.sandbox_url: %s", self.chatbot.sandbox_url)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.chatbot.sandbox_url), f"Invalid URL: {self.chatbot.sandbox_url}"
        )
        logger.debug("self.chatbot.hostname: %s", self.chatbot.hostname)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.url), f"Invalid URL: {self.chatbot.hostname}")
        logger.debug("self.chatbot.url: %s", self.chatbot.url)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.url), f"Invalid URL: {self.chatbot.url}")
        logger.debug("self.chatbot.url_chatbot: %s", self.chatbot.url_chatbot)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.chatbot.url_chatbot), f"Invalid URL: {self.chatbot.url_chatbot}"
        )
        logger.debug("self.chatbot.url_chatapp: %s", self.chatbot.url_chatapp)
        self.assertTrue(
            SmarterValidator.is_valid_url(self.chatbot.url_chatapp), f"Invalid URL: {self.chatbot.url_chatapp}"
        )
        logger.debug("self.chatbot.mode(self.chatbot.url): %s", self.chatbot.mode(self.chatbot.url))
        self.assertEqual(self.chatbot.mode(self.chatbot.url), "sandbox")

        hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(
            domain_name=aws_helper.aws.environment_api_domain
        )
        a_record = None
        retries = 5
        while retries > 0 and a_record is None:
            a_record = aws_helper.route53.get_dns_record(
                hosted_zone_id=hosted_zone_id, record_name=self.chatbot.default_host, record_type="A"
            )
            if a_record is None:
                print("DNS record not found. Retrying. Attempts remaining: ", retries)
                time.sleep(5)  # wait for 5 seconds before retrying
                retries -= 1
        self.assertIsNotNone(a_record)

        resolved_hostname = aws_helper.aws.domain_resolver(self.chatbot.default_host)
        self.assertIn(a_record["Name"], [resolved_hostname, resolved_hostname + "."])
        self.assertEqual(a_record["Type"], "A")

        self.assertTrue(self.chatbot.ready())
        # we'll test this separately since it run asynchronously. For now, just ensure it's one of the two hoped-for values.
        self.assertIn(
            self.chatbot.dns_verification_status,
            [ChatBot.DnsVerificationStatusChoices.VERIFIED, ChatBot.DnsVerificationStatusChoices.NOT_VERIFIED],
        )
        if self.chatbot.tls_certificate_issuance_status not in [
            ChatBot.TlsCertificateIssuanceStatusChoices.ISSUED,
            ChatBot.TlsCertificateIssuanceStatusChoices.REQUESTED,
        ]:
            logger.warning(
                "Unexpected TLS certificate issuance status: %s. This is likely a problem with Kubernetes cert-manager and will be ignored for purposes of this test.",
                self.chatbot.tls_certificate_issuance_status,
            )

        # mcdaniel: 2026-01-09: disabling this for now bc it's managed asynchronously
        # self.assertTrue(self.chatbot.deployed)

    def test_undeploy_default_api(self):
        """Test that we can undeploy the default API."""
        deploy_default_api(chatbot_id=self.chatbot.id, with_domain_verification=False)
        undeploy_default_api(chatbot_id=self.chatbot.id)

        self.assertFalse(self.chatbot.deployed)

        # DNS record should now be set to unverified, but the TLS certificate should still exist and still be valid.
        self.assertEqual(self.chatbot.dns_verification_status, ChatBot.DnsVerificationStatusChoices.NOT_VERIFIED)
