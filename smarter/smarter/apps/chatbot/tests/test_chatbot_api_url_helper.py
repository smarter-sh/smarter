# pylint: disable=wrong-import-position
"""Test ChatBotHelper."""

import logging

from django.contrib.auth import authenticate
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.handlers.wsgi import WSGIRequest
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.chatbot.models import ChatBot, ChatBotCustomDomain, ChatBotHelper
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# pylint: disable=too-many-instance-attributes
class TestChatBotApiUrlHelper(TestAccountMixin):
    """Test ChatBotHelper"""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.domain_name = f"test-bot-{self.hash_suffix}.{smarter_settings.environment_api_domain}"

        self.chatbot = ChatBot.objects.create(
            account=self.account,
            name=f"{self.hash_suffix}",
            deployed=True,
        )

        self.custom_domain_name = "smarter.querium.com"
        self.custom_domain = ChatBotCustomDomain.objects.create(
            account=self.account,
            domain_name=self.custom_domain_name,
            aws_hosted_zone_id="TEST_HOSTED_ZONE_ID",
            is_verified=True,
        )

        self.custom_chatbot = ChatBot.objects.create(
            account=self.account,
            name=f"test-custom-{self.hash_suffix}",
            custom_domain=self.custom_domain,
            deployed=True,
        )

        self.wsgi_request_factory = RequestFactory()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.chatbot.delete()
        except ChatBot.DoesNotExist:
            pass
        try:
            self.custom_chatbot.delete()
        except ChatBot.DoesNotExist:
            pass
        try:
            self.custom_domain.delete()
        except ChatBotCustomDomain.DoesNotExist:
            pass
        super().tearDown()

    def test_valid_url(self):
        """Test a url for the chatbot we created."""
        request: WSGIRequest = self.wsgi_request_factory.get(self.chatbot.url, SERVER_NAME="api.localhost:8000")
        user = authenticate(username=self.admin_user, password="12345")
        if user is None:
            self.fail("Authentication failed")
        request.user = user
        middleware = SessionMiddleware(lambda request: None)
        middleware.process_request(request)
        request.session.save()

        helper = ChatBotHelper(
            request=request,
            chatbot_id=self.chatbot.id,
            account=self.account,
            user=self.admin_user,
            user_profile=self.user_profile,
        )

        logger.info("dump: %s", helper.dump())
        self.assertTrue(
            helper.is_valid,
            f"Expected a chatbot helper to be valid, but got {helper.is_valid} for url {self.chatbot.url} -- helper: {helper}, user: {helper.user}, profile: {helper.user_profile}",
        )
        self.assertTrue(helper.account == self.account, f"Expected {self.account}, but got {helper.account}")
        self.assertTrue(
            helper.chatbot.url == self.chatbot.url, f"Expected {self.chatbot.url}, but got {helper.chatbot.url}"
        )
        self.assertTrue(helper.account_number == self.account.account_number)
        self.assertTrue(helper.is_custom_domain is False, f"this is not a default domain {helper.url}")
        self.assertTrue(helper.chatbot.deployed is True)

        # expecting http://api.localhost:8000/
        expected_url = f"http://{helper.api_host}/"
        self.assertTrue(
            expected_url == helper.url,
            f"Expected {helper.url}, but got {expected_url}",
        )

    def test_bad_url(self):
        """Test a bad url."""

        with self.assertRaises(Exception):
            ChatBotHelper(request=None, chatbot_id=-999999999)

    def test_non_api_url(self):
        """Test a non-api url."""
        request: WSGIRequest = self.wsgi_request_factory.get("/", SERVER_NAME="localhost:8000")
        helper = ChatBotHelper(
            request=request, chatbot_id=None, account=self.account, user=self.admin_user, user_profile=self.user_profile
        )

        self.assertFalse(helper.is_chatbot, f"Expected False, but got {helper.is_chatbot}")
        self.assertFalse(helper.is_smarter_api, f"Expected False, but got {helper.is_smarter_api}")
        self.assertFalse(helper.is_custom_domain)
        self.assertEqual(helper.account, self.account)
        self.assertIsNone(helper.chatbot, f"Expected None, but got {helper.chatbot}")
        self.assertEqual(helper.account_number, self.account.account_number)
        self.assertEqual(
            helper.api_host, "api.localhost:8000", f"Expected api.localhost:8000, but got {helper.api_host}"
        )
        self.assertIsNone(helper.api_subdomain, f"Expected None, but got {helper.api_subdomain}")

    def test_custom_domain(self):
        """Test a custom domain."""
        self.assertIsNotNone(self.custom_chatbot.id)
        url = self.custom_chatbot.url
        request: WSGIRequest = self.wsgi_request_factory.get(url, SERVER_NAME="smarter.querium.com")
        helper = ChatBotHelper(
            request=request,
            chatbot_id=self.custom_chatbot.id,
            account=self.account,
            user=self.admin_user,
            user_profile=self.user_profile,
        )

        chatbot = helper.chatbot

        self.assertEqual(self.custom_chatbot.name, chatbot.name)

        self.assertIsNotNone(helper.chatbot_id)
        self.assertIsNotNone(chatbot.url)
        self.assertEqual(self.custom_chatbot.url, chatbot.url)

        self.assertTrue(helper.is_valid, f"Expected True, but got {helper.to_json()}")
        self.assertTrue(helper.account == self.account, f"Expected {self.account}, but got {helper.account}")
        self.assertTrue(
            helper.chatbot == self.custom_chatbot, f"Expected {self.custom_chatbot}, but got {helper.chatbot}"
        )
        self.assertTrue(
            helper.account_number == self.account.account_number,
            f"Expected {self.account.account_number}, but got {helper.account_number}",
        )
        self.assertFalse(helper.is_custom_domain is True, f"Expected False, but got {helper.is_custom_domain}")
        self.assertIn(
            self.custom_chatbot.url,
            helper.chatbot.url,
            f"Expected {self.custom_chatbot.url}, but url {self.custom_chatbot.url} is not in {helper.chatbot.url}",
        )
        self.assertTrue(helper.chatbot.deployed)

    def test_no_url(self):
        """Test no url."""

        with self.assertRaises((SmarterValueError, TypeError)):
            ChatBotHelper()
