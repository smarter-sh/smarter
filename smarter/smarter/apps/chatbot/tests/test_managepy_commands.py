# pylint: disable=W0613
"""Tests for manage.py create_plugin."""

import logging
import time

from django.core.management import call_command

from smarter.apps.account.models import Account
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey
from smarter.apps.chatbot.signals import (
    chatbot_dns_failed,
    chatbot_dns_verification_initiated,
    chatbot_dns_verification_status_changed,
    chatbot_dns_verified,
)
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_EXAMPLE_CHATBOT_NAME
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# pylint: disable=too-many-instance-attributes
class ManageCommandCreatePluginTestCase(TestAccountMixin):
    """Tests for manage.py create_plugin."""

    _chatbot_dns_verification_status_changed = False
    _chatbot_dns_failed = False
    _chatbot_dns_verification_initiated = False
    _chatbot_dns_verified = False

    def chatbot_dns_verification_status_changed_signal_handler(self, *args, **kwargs):
        self._chatbot_dns_verification_status_changed = True

    def chatbot_dns_failed_signal_handler(self, *args, **kwargs):
        self._chatbot_dns_failed = True

    def chatbot_dns_verification_initiated_signal_handler(self, *args, **kwargs):
        self._chatbot_dns_verification_initiated = True

    def chatbot_dns_verified_signal_handler(self, *args, **kwargs):
        self._chatbot_dns_verified = True

    @property
    def signals(self):
        return {
            "chatbot_dns_verification_status_changed": self._chatbot_dns_verification_status_changed,
            "chatbot_dns_failed": self._chatbot_dns_failed,
            "chatbot_dns_verification_initiated": self._chatbot_dns_verification_initiated,
            "chatbot_dns_verified": self._chatbot_dns_verified,
        }

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.auth_token, self.secret_key = SmarterAuthToken.objects.create(
            name="testKey", user=self.admin_user, description="unit test"
        )  # type: ignore
        self.chatbot = ChatBot.objects.create(
            account=self.account,
            name="manage-command-create-plugin-test-case",
        )
        self._chatbot_dns_verification_status_changed = False
        self._chatbot_dns_failed = False
        self._chatbot_dns_verification_initiated = False
        self._chatbot_dns_verified = False

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            if self.chatbot is not None:
                self.chatbot.delete()
        except ChatBot.DoesNotExist:
            pass
        try:
            if self.auth_token is not None:
                self.auth_token.delete()
        except SmarterAuthToken.DoesNotExist:
            pass
        super().tearDown()

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

    def test_chatbot_dns_status_signals(self):
        chatbot_dns_verification_status_changed.connect(
            self.chatbot_dns_verification_status_changed_signal_handler,
            dispatch_uid="chatbot_dns_verification_status_changed_test_plugin_called_signal",
        )
        chatbot_dns_failed.connect(
            self.chatbot_dns_failed_signal_handler, dispatch_uid="chatbot_dns_failed_test_plugin_called_signal"
        )
        chatbot_dns_verification_initiated.connect(
            self.chatbot_dns_verification_initiated_signal_handler,
            dispatch_uid="chatbot_dns_verification_initiated_test_plugin_called_signal",
        )
        chatbot_dns_verified.connect(
            self.chatbot_dns_verified_signal_handler, dispatch_uid="chatbot_dns_verified_test_plugin_called_signal"
        )

        self.chatbot.dns_verification_status = ChatBot.DnsVerificationStatusChoices.VERIFYING
        self.chatbot.save()
        time.sleep(1)
        self.assertTrue(self.signals["chatbot_dns_verification_status_changed"])
        self.assertTrue(self.signals["chatbot_dns_verification_initiated"])

        self._chatbot_dns_verification_status_changed = False
        self.chatbot.dns_verification_status = ChatBot.DnsVerificationStatusChoices.FAILED
        self.chatbot.save()
        time.sleep(1)
        self.assertTrue(self.signals["chatbot_dns_verification_status_changed"])
        self.assertTrue(self.signals["chatbot_dns_failed"])

        self._chatbot_dns_verification_status_changed = False
        self.chatbot.dns_verification_status = ChatBot.DnsVerificationStatusChoices.VERIFIED
        self.chatbot.save()
        time.sleep(1)
        self.assertTrue(self.signals["chatbot_dns_verification_status_changed"])
        self.assertTrue(self.signals["chatbot_dns_verified"])

        self._chatbot_dns_verification_status_changed = False
        self.chatbot.dns_verification_status = ChatBot.DnsVerificationStatusChoices.NOT_VERIFIED
        self.chatbot.save()
        time.sleep(1)
        self.assertTrue(self.signals["chatbot_dns_verification_status_changed"])

    def test_deploy_and_undeploy(self):
        """Test deploy_chatbot and undeploy_chatbot commands."""

        #######################################################################
        # Deploy the chatbot
        #######################################################################
        print("test_deploy_and_undeploy(): initiating deploy...")
        print("-" * 80)

        # hosted zone for the Customer api domain
        api_hosted_zone_id = aws_helper.route53.get_hosted_zone_id_for_domain(
            domain_name=smarter_settings.environment_api_domain
        )

        call_command(
            "deploy_chatbot", "--account_number", f"{self.account.account_number}", "--name", self.chatbot.name
        )
        print("sleeping for 15 seconds to allow DNS record to be created")
        time.sleep(15)
        chatbot = ChatBot.objects.get(name=self.chatbot.name, account=self.account)
        print(f"found chatbot.id={chatbot.id} chatbot.default_host={chatbot.default_host}")

        # verify that a DNS record was created for the chatbot
        chatbot_default_host = chatbot.default_host
        a_record = aws_helper.route53.get_dns_record(
            hosted_zone_id=api_hosted_zone_id, record_name=chatbot_default_host, record_type="A"
        )
        self.assertIsNotNone(
            a_record, f"DNS A record not found for hosted zone {api_hosted_zone_id}, {chatbot_default_host}"
        )
        resolved_chatbot_domain = aws_helper.aws.domain_resolver(chatbot_default_host)
        if not isinstance(a_record, dict):
            self.fail(f"Unexpected DNS record format for {chatbot_default_host}: {a_record}")
        self.assertEqual(str(a_record["Name"]).rstrip("."), str(resolved_chatbot_domain).rstrip("."))

        # verify that the dns record verification is either underway or completed
        print("chatbot.dns_verification_status", chatbot.dns_verification_status)
        self.assertIn(
            chatbot.dns_verification_status,
            [chatbot.DnsVerificationStatusChoices.VERIFYING, chatbot.DnsVerificationStatusChoices.VERIFIED],
        )

        #######################################################################
        # Undeploy the chatbot
        #######################################################################
        print("test_deploy_and_undeploy(): initiating undeploy...")
        print("-" * 80)

        call_command(
            "undeploy_chatbot",
            "--account_number",
            f"{self.account.account_number}",
            "--name",
            self.chatbot.name,
            "--foreground",
        )
        chatbot = ChatBot.objects.get(name=self.chatbot.name, account=self.account)
        self.assertEqual(chatbot.deployed, False)
        self.assertEqual(chatbot.dns_verification_status, chatbot.DnsVerificationStatusChoices.NOT_VERIFIED)
        a_record = aws_helper.route53.get_dns_record(
            hosted_zone_id=api_hosted_zone_id,
            record_name=chatbot_default_host,
            record_type="A",
        )
        if a_record is not None:
            logger.info("test_deploy_and_undeploy() found an existing DNS record: %s", a_record)
            resolved_chatbot_domain = aws_helper.aws.domain_resolver(chatbot_default_host)
            self.assertEqual(str(a_record["Name"]).rstrip("."), str(resolved_chatbot_domain).rstrip("."))

    def test_deploy_demo_api(self):
        """Test deploy_example_chatbot command."""
        call_command("deploy_example_chatbot")
        print("sleeping for 15 seconds to allow DNS record to be created")
        time.sleep(15)

        account = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        chatbot = ChatBot.objects.get(name=SMARTER_EXAMPLE_CHATBOT_NAME, account=account)
        self.assertIn(
            chatbot.dns_verification_status,
            [chatbot.DnsVerificationStatusChoices.VERIFYING, chatbot.DnsVerificationStatusChoices.VERIFIED],
        )

    def test_initialize_waffle(self):
        """Test initialize_waffle command."""
        call_command("initialize_waffle")

    def test_load_from_github_v1(self):
        """Test load_from_github command."""

        call_command(
            "load_from_github",
            "--account_number",
            f"{self.account.account_number}",
            "--url",
            "https://github.com/QueriumCorp/smarter-demo",
            "--username",
            self.admin_user.get_username(),
        )

    def test_load_from_github_v2(self):
        """Test load_from_github command."""

        call_command(
            "load_from_github",
            "--account_number",
            f"{self.account.account_number}",
            "--url",
            "https://github.com/smarter-sh/examples",
            "--username",
            self.admin_user.get_username(),
            "--repo_version",
            "2",
        )

    def test_verify_api_infrastructure(self):
        """Test verify_dns_configuration command."""

        call_command("verify_dns_configuration")
