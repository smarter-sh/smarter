# pylint: disable=wrong-import-position
"""Test ChatBotApiUrlHelper."""

# python stuff
import hashlib
import random
import unittest
from urllib.parse import urljoin

from django.contrib.auth import get_user_model

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotApiUrlHelper,
    ChatBotCustomDomain,
)
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError


User = get_user_model()


# pylint: disable=too-many-instance-attributes
class TestChatBotApiUrlHelper(unittest.TestCase):
    """Test ChatBotApiUrlHelper"""

    def setUp(self):
        """Set up test fixtures."""
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
        self.domain_name = f"{hashed_slug}.{smarter_settings.customer_api_domain}"

        username = f"test_{hashed_slug}"

        self.user = User.objects.create(username=username, password="12345")
        self.account = Account.objects.create(company_name=f"Test_{hashed_slug}", phone_number="123-456-789")
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)

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
        self.user_profile.delete()
        self.account.delete()
        self.user.delete()
        self.custom_chatbot.delete()
        self.custom_domain.delete()

    def test_valid_url(self):
        """Test a url for the chatbot we created."""
        helper = ChatBotApiUrlHelper(url=self.chatbot.url, environment=smarter_settings.environment)

        self.assertTrue(helper.is_valid)
        self.assertTrue(helper.account == self.account)
        self.assertTrue(helper.chatbot == self.chatbot)
        self.assertTrue(helper.account_number == self.account.account_number)
        self.assertTrue(helper.is_custom_domain is False)
        self.assertTrue(helper.url == self.chatbot.url)
        self.assertTrue(helper.is_deployed is True)
        self.assertTrue(helper.api_host == smarter_settings.customer_api_domain)
        self.assertTrue(helper.api_subdomain == self.chatbot.name)
        self.assertTrue(helper.customer_api_domain == smarter_settings.customer_api_domain)
        self.assertTrue(helper.environment == smarter_settings.environment)

    def test_bad_url(self):
        """Test a bad url."""

        with self.assertRaises(SmarterValueError):
            ChatBotApiUrlHelper(url="bad url")

    def test_non_api_url(self):
        """Test a non-api url."""
        helper = ChatBotApiUrlHelper(url="https://www.google.com")

        self.assertTrue(helper.account is None)
        self.assertTrue(helper.chatbot is None)
        self.assertTrue(helper.account_number is None)
        self.assertTrue(helper.is_custom_domain is False)
        self.assertTrue(helper.url == "https://www.google.com")
        self.assertTrue(helper.is_deployed is False)
        self.assertTrue(helper.api_host is None)
        self.assertTrue(helper.api_subdomain is None)
        self.assertTrue(helper.customer_api_domain == smarter_settings.customer_api_domain)
        self.assertTrue(helper.environment is None)

    def test_custom_domain(self):
        """Test a custom domain."""
        url = urljoin(self.custom_chatbot.url, "/chatbot/")
        helper = ChatBotApiUrlHelper(url=url)

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
        self.assertIn(self.custom_chatbot.url, helper.url, f"Expected {self.custom_chatbot.url}, but got {helper.url}")
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
            helper.environment is None, f"Expected {smarter_settings.environment}, but got {helper.environment}"
        )
