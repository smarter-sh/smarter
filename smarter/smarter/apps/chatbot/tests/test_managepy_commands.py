"""Tests for manage.py create_plugin."""

import hashlib
import random
import time
import unittest

from django.core.management import call_command

from smarter.apps.account.models import Account, SmarterAuthToken
from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_CHATBOT_NAME
from smarter.common.helpers.aws_helpers import aws_helper


class ManageCommandCreatePluginTestCase(unittest.TestCase):
    """Tests for manage.py create_plugin."""

    def setUp(self):
        """Set up test fixtures."""
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
        self.user, self.account, self.user_profile = admin_user_factory()
        self.auth_token, self.secret_key = SmarterAuthToken.objects.create(
            account=self.account, user=self.user, description="unit test"
        )
        self.chatbot = ChatBot.objects.create(
            account=self.account,
            name=f"{hashed_slug}",
        )

    def tearDown(self):
        """Clean up test fixtures."""
        admin_user_teardown(self.user, self.account, self.user_profile)

    def test_add_api_key(self):
        """Test add_api_key command."""

        call_command(
            "add_api_key",
            "--account_number",
            f"{self.account.account_number}",
            "--key_id",
            self.auth_token.key_id,
            "--name",
            self.chatbot.name,
        )

        chatbot_api_key = ChatBotAPIKey.objects.get(api_key=self.auth_token)
        self.assertEqual(chatbot_api_key.chatbot, self.chatbot)

    def test_deploy_and_undeploy(self):
        """Test deploy_api and undeploy_api commands."""

        # hosted zone for the Customer api domain
        api_hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(
            domain_name=smarter_settings.customer_api_domain
        )

        call_command("deploy_api", "--account_number", f"{self.account.account_number}", "--name", self.chatbot.name)
        print("sleeping for 3 seconds to allow DNS record to be created")
        time.sleep(3)
        chatbot = ChatBot.objects.get(name=self.chatbot.name, account=self.account)

        # verify that a DNS record was created for the chatbot
        chatbot_default_host = chatbot.default_host
        a_record = aws_helper.route53.get_dns_record(
            hosted_zone_id=api_hosted_zone_id, record_name=chatbot_default_host, record_type="A"
        )
        self.assertIsNotNone(a_record)
        resolved_chatbot_domain = aws_helper.aws.domain_resolver(chatbot_default_host)
        self.assertEqual(str(a_record["Name"]).rstrip("."), str(resolved_chatbot_domain).rstrip("."))

        # verify that the dns record verification is either underway or completed
        print("chatbot.dns_verification_status", chatbot.dns_verification_status)
        self.assertIn(
            chatbot.dns_verification_status,
            [chatbot.DnsVerificationStatusChoices.VERIFYING, chatbot.DnsVerificationStatusChoices.VERIFIED],
        )

        call_command(
            "undeploy_api",
            "--account_number",
            f"{self.account.account_number}",
            "--name",
            self.chatbot.name,
            "--foreground",
        )
        chatbot = ChatBot.objects.filter(name=self.chatbot.name, account=self.account).first()
        self.assertIsNone(chatbot)
        a_record = aws_helper.route53.get_dns_record(
            hosted_zone_id=api_hosted_zone_id, record_name=chatbot_default_host
        )
        self.assertIsNone(a_record)

    def test_deploy_demo_api(self):
        """Test deploy_demo_api command."""
        call_command("deploy_demo_api")
        print("sleeping for 10 seconds to allow DNS record to be created")

        account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        chatbot = ChatBot.objects.get(name=SMARTER_EXAMPLE_CHATBOT_NAME, account=account)
        print("chatbot.dns_verification_status", chatbot.dns_verification_status)
        self.assertIn(
            chatbot.dns_verification_status,
            [chatbot.DnsVerificationStatusChoices.VERIFYING, chatbot.DnsVerificationStatusChoices.VERIFIED],
        )

    def test_initialize_waffle(self):
        """Test initialize_waffle command."""
        call_command("initialize_waffle")

    def test_load_from_github(self):
        """Test load_from_github command."""

        call_command(
            "load_from_github",
            "--account_number",
            f"{self.account.account_number}",
            "--url",
            "https://github.com/QueriumCorp/smarter-demo",
            "--username",
            self.user.get_username(),
        )

    def test_verify_api_infrastructure(self):
        """Test verify_api_infrastructure command."""

        call_command("verify_api_infrastructure")
