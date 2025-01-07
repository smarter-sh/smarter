# pylint: disable=wrong-import-position
"""Test ChatBotHelper."""

# python stuff
import hashlib
import random
import unittest
from urllib.parse import urljoin

from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.chatbot.models import ChatBot, ChatBotCustomDomain, ChatBotHelper
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django.validators import SmarterValidator


# pylint: disable=too-many-instance-attributes
class TestChatBotApiUrlHelper(unittest.TestCase):
    """Test ChatBotHelper"""

    def setUp(self):
        """Set up test fixtures."""
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
        self.domain_name = f"{hashed_slug}.{smarter_settings.customer_api_domain}"

        self.user, self.account, self.user_profile = admin_user_factory()

        self.chatbot = ChatBot.objects.create(
            account=self.account,
            name=f"{hashed_slug}",
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
            name=f"custom-{hashed_slug}",
            custom_domain=self.custom_domain,
            deployed=True,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.chatbot.delete()
        self.custom_chatbot.delete()
        self.custom_domain.delete()
        admin_user_teardown(user=self.user, account=self.account, user_profile=self.user_profile)

    def test_valid_url(self):
        """Test a url for the chatbot we created."""
        helper = ChatBotHelper(url=self.chatbot.url, environment=smarter_settings.environment)

        self.assertTrue(helper.is_valid)
        self.assertTrue(helper.account == self.account)
        self.assertTrue(
            helper.chatbot.url == self.chatbot.url, f"Expected {self.chatbot.url}, but got {helper.chatbot.url}"
        )
        self.assertTrue(helper.account_number == self.account.account_number)
        self.assertTrue(helper.is_custom_domain is False, f"this is not a default domain {helper.url}")
        self.assertTrue(
            SmarterValidator.urlify(helper.url, environment=smarter_settings.environment)
            == SmarterValidator.urlify(self.chatbot.url, environment=smarter_settings.environment)
        )
        self.assertTrue(helper.is_deployed is True)
        self.assertTrue(
            helper.api_host == smarter_settings.customer_api_domain,
            f"Expected {smarter_settings.customer_api_domain}, but got {helper.api_host}",
        )
        self.assertTrue(helper.api_subdomain == self.chatbot.name)
        self.assertTrue(helper.customer_api_domain == smarter_settings.customer_api_domain)
        self.assertTrue(helper.environment == smarter_settings.environment)

    def test_bad_url(self):
        """Test a bad url."""

        with self.assertRaises(Exception):
            ChatBotHelper(url="bad url")

    def test_non_api_url(self):
        """Test a non-api url."""
        helper = ChatBotHelper(url="https://www.google.com")
        reschemed_url = SmarterValidator.urlify(helper.url, environment=smarter_settings.environment)

        self.assertTrue(helper.account is None)
        self.assertTrue(helper.chatbot is None)
        self.assertTrue(helper.account_number is None)
        self.assertTrue(helper.is_custom_domain is False)
        self.assertTrue(
            str(reschemed_url) == "http://www.google.com/",
            f"Expected http://www.google.com, but got {reschemed_url}",
        )
        self.assertTrue(helper.is_deployed is False)
        self.assertTrue(helper.api_host is None)
        self.assertTrue(helper.api_subdomain == "www")
        self.assertTrue(helper.customer_api_domain == smarter_settings.customer_api_domain)
        self.assertTrue(helper.environment is not None)

    def test_custom_domain(self):
        """Test a custom domain."""
        url = urljoin(self.custom_chatbot.url, "/api/v1/chatbots/smarter/" + self.chatbot.name + "/")
        helper = ChatBotHelper(url=url, account=self.account, user=self.user)

        self.assertTrue(helper.is_valid)
        self.assertTrue(helper.account == self.account, f"Expected {self.account}, but got {helper.account}")
        self.assertTrue(
            helper.chatbot == self.custom_chatbot, f"Expected {self.custom_chatbot}, but got {helper.chatbot}"
        )
        self.assertTrue(
            helper.account_number == self.account.account_number,
            f"Expected {self.account.account_number}, but got {helper.account_number}",
        )
        self.assertTrue(helper.is_custom_domain is True, f"Expected True, but got {helper.is_custom_domain}")
        self.assertIn(
            SmarterValidator.urlify(self.custom_chatbot.url, environment=smarter_settings.environment),
            SmarterValidator.urlify(helper.url, environment=smarter_settings.environment),
            f"Expected {self.custom_chatbot.url}, but got {helper.url}",
        )
        self.assertTrue(helper.is_deployed is True, f"Expected True, but got {helper.is_deployed}")
        self.assertTrue(
            helper.api_host == self.custom_domain.domain_name,
            f"Expected {self.custom_domain.domain_name}, but got {helper.api_host}",
        )
        self.assertTrue(
            helper.api_subdomain == self.custom_chatbot.name,
            f"Expected {self.custom_chatbot.name}, but got {helper.api_subdomain}",
        )
        self.assertTrue(
            helper.customer_api_domain == smarter_settings.customer_api_domain,
            f"Expected {smarter_settings.customer_api_domain}, but got {helper.customer_api_domain}",
        )
        self.assertTrue(
            helper.environment == smarter_settings.environment,
            f"Expected {smarter_settings.environment}, but got {helper.environment}",
        )

    def test_no_url(self):
        """Test no url."""
        helper = ChatBotHelper()

        self.assertTrue(helper.is_valid is False)
        self.assertTrue(helper.account is None)
        self.assertTrue(helper.chatbot is None)
        self.assertTrue(helper.account_number is None)
        self.assertTrue(helper.is_custom_domain is False)
        self.assertTrue(helper.url is None)
        self.assertTrue(helper.is_deployed is False)
        self.assertTrue(helper.api_host is None)
        self.assertTrue(helper.api_subdomain is None)
        self.assertTrue(helper.customer_api_domain == smarter_settings.customer_api_domain)
        self.assertTrue(helper.environment is not None)
