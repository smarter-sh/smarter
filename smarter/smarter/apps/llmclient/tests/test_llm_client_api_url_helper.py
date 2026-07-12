# pylint: disable=wrong-import-position
"""Test LLMClientHelper."""

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.handlers.asgi import ASGIRequest
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientCustomDomain,
    LLMClientHelper,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


# pylint: disable=too-many-instance-attributes
class TestLLMClientApiUrlHelper(TestAccountMixin):
    """Test LLMClientHelper."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.domain_name = "foo.com"
        settings.ALLOWED_HOSTS.append(self.domain_name)

        self.llmclient = LLMClient.objects.create(
            user_profile=self.user_profile,
            name=f"test-{self.hash_suffix}",
            deployed=True,
        )

        self.custom_domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile,
            domain_name=self.domain_name,
            aws_hosted_zone_id="TEST_HOSTED_ZONE_ID",
            is_verified=True,
        )

        self.custom_llmclient = LLMClient.objects.create(
            user_profile=self.user_profile,
            name=f"test-custom-{self.hash_suffix}",
            custom_domain=self.custom_domain,
            deployed=True,
        )

        self.wsgi_request_factory = RequestFactory()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.llmclient.delete()
        except LLMClient.DoesNotExist:
            pass
        try:
            self.custom_llmclient.delete()
        except LLMClient.DoesNotExist:
            pass
        try:
            self.custom_domain.delete()
        except LLMClientCustomDomain.DoesNotExist:
            pass
        super().tearDown()

    def test_valid_url(self):
        """Test a url for the llmclient we created."""
        url = self.llmclient.url
        logger.debug("test_valid_url() llmclient url: %s", url)
        parsed = urlparse(url)
        http_host = parsed.netloc
        settings.ALLOWED_HOSTS.append(http_host)
        request = RequestFactory().get(
            parsed.path or "/",
            HTTP_HOST=http_host,
        )
        user = authenticate(username=self.admin_user, password="12345")
        if user is None:
            self.fail("Authentication failed")
        request.user = user
        middleware = SessionMiddleware(lambda request: None)
        middleware.process_request(request)
        request.session.save()

        helper = LLMClientHelper(
            request=request,
            llmclient_id=self.llmclient.id,
            account=self.account,
            user=self.admin_user,
            user_profile=self.user_profile,
        )

        self.assertTrue(
            helper.ready,
            f"Expected an llmclient helper to be valid, but got {helper.ready} for url {self.llmclient.url} -- helper: {helper}, user: {helper.user}, profile: {helper.user_profile}",
        )
        self.assertTrue(helper.account == self.account, f"Expected {self.account}, but got {helper.account}")
        self.assertTrue(
            helper.llmclient.url == self.llmclient.url,
            f"Expected {self.llmclient.url}, but got {helper.llmclient.url}",
        )
        self.assertTrue(helper.account_number == self.account.account_number)
        self.assertTrue(helper.is_custom_domain is False, f"this is not a default domain {helper.url}")
        self.assertTrue(helper.llmclient.deployed is True)

    def test_bad_url(self):
        """Test a bad url."""

        with self.assertRaises(Exception):
            LLMClientHelper(request=None, llmclient_id=-999999999)

    def test_non_api_url(self):
        """Test a non-api url."""
        request: ASGIRequest = self.wsgi_request_factory.get("/", SERVER_NAME="localhost:9357")
        helper = LLMClientHelper(
            request=request,
            llmclient_id=None,
            account=self.account,
            user=self.admin_user,
            user_profile=self.user_profile,
        )

        self.assertFalse(helper.is_llmclient, f"Expected False, but got {helper.is_llmclient}")
        self.assertFalse(helper.is_smarter_api, f"Expected False, but got {helper.is_smarter_api}")
        self.assertFalse(helper.is_custom_domain)
        self.assertEqual(helper.account, self.account)
        self.assertIsNone(helper.llmclient, f"Expected None, but got {helper.llmclient}")
        self.assertEqual(helper.account_number, self.account.account_number)
        self.assertEqual(
            helper.api_host, "api.localhost:9357", f"Expected api.localhost:9357, but got {helper.api_host}"
        )
        self.assertIsNone(helper.api_subdomain, f"Expected None, but got {helper.api_subdomain}")

    def test_custom_domain(self):
        """Test a custom domain."""

        self.assertIsNotNone(self.custom_llmclient.id)
        url = self.custom_llmclient.url
        logger.debug("test_custom_domain() custom llmclient url: %s", url)
        parsed = urlparse(url)
        http_host = parsed.netloc
        settings.ALLOWED_HOSTS.append(http_host)
        request = RequestFactory().get(
            parsed.path or "/",
            HTTP_HOST=http_host,
        )

        helper = LLMClientHelper(
            request=request,
            llmclient_id=self.custom_llmclient.id,
            account=self.account,
            user=self.admin_user,
            user_profile=self.user_profile,
        )

        llmclient = helper.llmclient

        self.assertEqual(self.custom_llmclient.name, llmclient.name)

        self.assertIsNotNone(helper.llmclient_id)
        self.assertIsNotNone(llmclient.url)
        self.assertEqual(self.custom_llmclient.url, llmclient.url)

        self.assertTrue(helper.ready, f"Expected True, but got {helper.to_json()}")
        self.assertTrue(helper.account == self.account, f"Expected {self.account}, but got {helper.account}")
        self.assertTrue(
            helper.llmclient == self.custom_llmclient,
            f"Expected {self.custom_llmclient}, but got {helper.llmclient}",
        )
        self.assertTrue(
            helper.account_number == self.account.account_number,
            f"Expected {self.account.account_number}, but got {helper.account_number}",
        )
        self.assertTrue(helper.is_custom_domain)
        self.assertIn(
            self.custom_llmclient.url,
            helper.llmclient.url,
            f"Expected {self.custom_llmclient.url}, but url {self.custom_llmclient.url} is not in {helper.llmclient.url}",
        )
        self.assertTrue(helper.llmclient.deployed)

    def test_no_url(self):
        """Test no url."""

        with self.assertRaises((SmarterValueError, TypeError)):
            LLMClientHelper()
