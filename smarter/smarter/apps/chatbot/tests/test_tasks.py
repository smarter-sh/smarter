# pylint: disable=wrong-import-position
"""Test Chatbot tasks."""

# python stuff
import hashlib
import random
import time
import unittest

from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.chatbot.models import ChatBot, ChatBotCustomDomain
from smarter.common.conf import settings as smarter_settings
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib.django.validators import SmarterValidator

from ..tasks import (  # register_custom_domain,; verify_custom_domain,
    create_custom_domain_dns_record,
    create_domain_A_record,
    deploy_default_api,
    verify_domain,
)


class TestChatBotTasks(unittest.TestCase):
    """Test Chatbot tasks"""

    def setUp(self):
        """Set up test fixtures."""
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
        self.domain_name = f"{hashed_slug}.{aws_helper.aws.customer_api_domain}"
        self.hosted_zone = aws_helper.route53.get_hosted_zone(domain_name=self.domain_name)
        if self.hosted_zone:
            aws_helper.route53.delete_hosted_zone(domain_name=self.domain_name)
        self.user, self.account, self.user_profile = admin_user_factory()

        self.chatbot = ChatBot.objects.create(
            account=self.account,
            name=f"{hashed_slug}",
        )

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            ChatBotCustomDomain.objects.get(account_id=self.account.id).delete()
        except ChatBotCustomDomain.DoesNotExist:
            pass
        self.chatbot.delete()
        admin_user_teardown(self.user, self.account, self.user_profile)

        self.hosted_zone = aws_helper.route53.get_hosted_zone(domain_name=self.domain_name)
        if self.hosted_zone:
            aws_helper.route53.delete_hosted_zone(domain_name=self.domain_name)
        certificate_arn = aws_helper.acm.get_certificate_arn(domain_name=self.domain_name)
        if certificate_arn:
            aws_helper.acm.delete_certificate(certificate_arn=certificate_arn)

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
            account=self.account,
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
        hosted_zone = aws_helper.route53.get_hosted_zone(domain_name=aws_helper.aws.customer_api_domain)
        hosted_zone_id = aws_helper.route53.get_hosted_zone_id(hosted_zone=hosted_zone)

        print("resolved_domain", resolved_domain)
        print("hosted_zone", hosted_zone)
        print("hosted_zone_id", hosted_zone_id)
        dns_record = create_domain_A_record(
            hostname=resolved_domain, api_host_domain=aws_helper.aws.customer_api_domain
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

        print("self.chatbot.default_host", self.chatbot.default_host)
        self.assertTrue(SmarterValidator.is_valid_hostname(self.chatbot.default_host))
        print("self.chatbot.default_url", self.chatbot.default_url)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.default_url))
        print("self.chatbot.custom_host", self.chatbot.custom_host)
        self.assertIsNone(self.chatbot.custom_host)
        print("self.chatbot.custom_url", self.chatbot.custom_url)
        self.assertIsNone(self.chatbot.custom_url)
        print("self.chatbot.sandbox_host", self.chatbot.sandbox_host)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.sandbox_host))
        print("self.chatbot.sandbox_url", self.chatbot.sandbox_url)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.sandbox_url))
        print("self.chatbot.hostname", self.chatbot.hostname)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.hostname))
        print("self.chatbot.scheme", self.chatbot.scheme)
        self.assertEqual(self.chatbot.scheme, "http")
        print("self.chatbot.url", self.chatbot.url)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.url))
        print("self.chatbot.url_chatbot", self.chatbot.url_chatbot)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.url_chatbot))
        print("self.chatbot.url_chatapp", self.chatbot.url_chatapp)
        self.assertTrue(SmarterValidator.is_valid_url(self.chatbot.url_chatapp))
        print("self.chatbot.mode(self.chatbot.url)", self.chatbot.mode(self.chatbot.url))
        self.assertEqual(self.chatbot.mode(self.chatbot.url), "sandbox")

        hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(
            domain_name=aws_helper.aws.customer_api_domain
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
