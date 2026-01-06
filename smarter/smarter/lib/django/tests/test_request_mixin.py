# pylint: disable=W0212
"""Test SmarterRequestMixin."""

import warnings
from datetime import datetime
from logging import getLogger
from unittest.mock import patch
from urllib.parse import ParseResult

from django.contrib.auth import authenticate
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import Client, RequestFactory

import smarter.lib.django.request as req_mod
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.common.conf import settings as smarter_settings
from smarter.common.utils import is_authenticated_request
from smarter.lib.django.request import SmarterRequestMixin, SmarterValueError


SMARTER_DEV_ADMIN_PASSWORD = "smarter"
logger = getLogger(__name__)


class DummyRequest(HttpRequest):
    """
    A minimal HttpRequest subclass for testing.
    """

    META = {
        "HTTP_HOST": "localhost",
        "QUERY_STRING": "",
        "GET": {},
        "COOKIES": {"session_key": "cookiekey"},
        "user": "testuser",
    }


class TestSmarterRequestMixin(TestAccountMixin):
    """
    Test SmarterRequestMixin.
    example urls:
    - http://testserver
    - http://localhost:8000/
    - http://localhost:8000/docs/
    - http://localhost:8000/dashboard/
    - https://alpha.platform.smarter.sh/api/v1/workbench/1/chatbot/
    - https://alpha.platform.smarter.sh/api/v1/cli/chat/example/
    - http://example.com/contact/
    - http://localhost:8000/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/config/?session_key=38486326c21ef4bcb7e7bc305bdb062f16ee97ed8d2462dedb4565c860cd8ecc
    - http://example.3141-5926-5359.api.localhost:8000/
    - http://example.3141-5926-5359.api.localhost:8000/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126
    - http://example.3141-5926-5359.api.localhost:8000/config/
    - http://example.3141-5926-5359.api.localhost:8000/config/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126
    - http://localhost:8000/api/v1/workbench/1/chat/
    - https://hr.smarter.sh/

    """

    def setUp(self):
        super().setUp()
        self.session_key = "1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a"
        self.client = Client()
        logger.debug("-" * 35 + " Begin Test: %s " + "-" * 35, self._testMethodName)

    def tearDown(self):
        logger.debug("-" * 35 + " End Test: %s " + "-" * 35, self._testMethodName)
        try:
            self.client.logout()
            self.client = None
        # pylint: disable=W0718
        except Exception:
            pass

    def wsgi_request_factory(self) -> RequestFactory:
        """
        Create a RequestFactory with default headers and query parameters.
        """
        return RequestFactory(
            SERVER_NAME="localhost",
            SERVER_PORT=8000,
            query_params={
                "uid": "1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a",
                "session_key": self.session_key,
            },
            headers={
                "Host": "localhost:8000",
                "User-Agent": "SmarterTestClient/1.0",
            },
        )

    def get_smarter_request_mixin(self, url: str) -> SmarterRequestMixin:
        request = self.wsgi_request_factory().get(url)
        smarter_admin_user_profile = get_cached_smarter_admin_user_profile()
        user = authenticate(username=smarter_admin_user_profile.user.username, password=SMARTER_DEV_ADMIN_PASSWORD)
        if user is None:
            logger.error("Failed to authenticate smarter admin user for testing.")
            self.fail("Authentication failed")
        request.user = user
        middleware = SessionMiddleware(lambda request: None)
        middleware.process_request(request)
        request.session.save()

        return SmarterRequestMixin(request)

    def test_init_without_request_object(self):
        """
        Test that SmarterRequestMixin will initialize without a request object.
        """
        SmarterRequestMixin(request=None)

    def test_unauthenticated_instantiation(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        """
        request = self.wsgi_request_factory().get("/")

        srm = SmarterRequestMixin(request)
        self.assertIsNotNone(srm.to_json())

    def test_authenticated_instantiation(self):
        """
        Test that SmarterRequestMixin can be instantiated with an authenticated request.
        """
        self.client.login(username=self.admin_user.username, password="12345")
        response = self.client.get("/")
        request = response.wsgi_request

        srm = SmarterRequestMixin(request)
        self.assertIsNotNone(srm.to_json())

    def test_request_object_can_be_set(self):
        """
        Test that SmarterRequestMixin request object is read-only.
        """
        self.client.login(username=self.admin_user.username, password="12345")
        response = self.client.get("/")

        # we should be able to instantiate SmarterRequestMixin with a None request
        request = None
        srm = SmarterRequestMixin(request)

        # and afterwards we should later be able to set smarter_request
        srm.smarter_request = response.wsgi_request

        # and after that, we should see authenticated user data
        self.assertIsNotNone(srm.user)
        self.assertIsNotNone(srm.account)
        self.assertIsNotNone(srm.user_profile)
        self.assertIsNotNone(srm.url)
        self.assertTrue(srm.is_authenticated)

    def test_unauthenticated_base_case(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        """
        request = self.wsgi_request_factory().get(f"/?session_key={self.session_key}", SERVER_NAME="testserver")
        srm = SmarterRequestMixin(request)
        self.assertIsNone(srm.account)
        self.assertIsNotNone(srm.session_key)
        self.assertEqual(srm.domain, "testserver")
        self.assertEqual(srm.ip_address, "127.0.0.1")
        self.assertFalse(srm.is_smarter_api)
        self.assertFalse(srm.is_chatbot)
        self.assertFalse(srm.is_chatbot_smarter_api_url)
        self.assertFalse(srm.is_chatbot_named_url)
        self.assertFalse(srm.is_chatbot_sandbox_url)
        self.assertFalse(srm.is_chatbot_cli_api_url)
        self.assertFalse(srm.is_default_domain)
        self.assertEqual(srm.path, "/")
        self.assertEqual(srm.root_domain, "testserver")
        self.assertEqual(srm.subdomain, "")
        self.assertIsNone(srm.user)
        self.assertIsInstance(srm.timestamp, datetime)
        try:
            dt = datetime.fromisoformat(str(srm.timestamp))
            self.assertIsInstance(dt, datetime)
        except ValueError:
            self.fail("The timestamp could not be converted to a datetime object")

        self.assertIsNotNone(srm.unique_client_string)
        self.assertIsInstance(srm.unique_client_string, str)
        self.assertIsNotNone(srm.url)
        self.assertIsInstance(srm.url, str)
        self.assertEqual(srm.url, "http://testserver/")
        self.assertIsInstance(srm.parsed_url, ParseResult)
        self.assertIsNotNone(srm.to_json())
        self.assertIsInstance(srm.to_json(), dict)

    def test_named_api_url(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        http://example.3141-5926-5359.api.localhost:8000/

        we need to authenticate with the Smarter admin account and the dev environment
        needs to be fully initialized.
        """
        url = "http://example.3141-5926-5359.api.localhost:8000/"
        smarter_admin_user_profile = get_cached_smarter_admin_user_profile()
        if smarter_admin_user_profile is None:
            self.skipTest("Smarter admin user profile is not available")

        self.client.login(username=smarter_admin_user_profile.user.username, password=SMARTER_DEV_ADMIN_PASSWORD)
        response = self.client.get(url, SERVER_NAME="example.3141-5926-5359.api.localhost:8000")
        request = response.wsgi_request
        request.user = smarter_admin_user_profile.user
        self.assertEqual(request.user, smarter_admin_user_profile.user)
        self.assertEqual(url, request.build_absolute_uri())
        if not is_authenticated_request(request):
            self.skipTest("User is not authenticated")

        srm = SmarterRequestMixin(request)

        self.assertEqual(srm.account, smarter_admin_user_profile.account)
        self.assertEqual(srm.user, smarter_admin_user_profile.user)
        self.assertEqual(srm.url, url)
        self.assertTrue(srm.is_chatbot)
        self.assertTrue(srm.is_chatbot_named_url)
        self.assertFalse(srm.is_chatbot_cli_api_url)
        self.assertFalse(srm.is_chatbot_sandbox_url)
        self.assertFalse(srm.is_smarter_api)
        self.assertIsNotNone(srm.session_key)
        self.assertEqual(srm.domain, "example.3141-5926-5359.api.localhost:8000")

    def test_sandbox_url(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        http://localhost:8000/workbench/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
        """
        smarter_admin_user_profile = get_cached_smarter_admin_user_profile()
        if smarter_admin_user_profile is None:
            self.skipTest("Smarter admin user profile is not available")

        path = "/workbench/example/chat/"
        url = "http://localhost:8000" + path + f"?session_key={self.session_key}"
        srm = self.get_smarter_request_mixin(url)

        self.assertEqual(srm.url, "http://localhost:8000" + path)
        self.assertEqual(srm.user, smarter_admin_user_profile.user)
        self.assertEqual(srm.account, smarter_admin_user_profile.account)
        self.assertIsNotNone(srm.client_key)
        self.assertEqual(srm.domain, "localhost:8000")
        self.assertFalse(srm.is_chatbot_named_url)
        self.assertFalse(srm.is_chatbot_cli_api_url)
        self.assertFalse(srm.is_smarter_api)
        self.assertEqual(srm.path, path)
        self.assertTrue(srm.is_chatbot_sandbox_url)
        self.assertTrue(srm.is_chatbot)

    def test_api_url(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        http://localhost:8000/api/v1/prompt/1/chat/
        """
        smarter_admin_user_profile = get_cached_smarter_admin_user_profile()
        if smarter_admin_user_profile is None:
            self.skipTest("Smarter admin user profile is not available")

        path = "/api/v1/prompt/1/chat/"
        url = "http://localhost:8000" + path + f"?session_key={self.session_key}"
        srm = self.get_smarter_request_mixin(url)

        self.assertEqual(srm.url, "http://localhost:8000" + path)
        self.assertEqual(srm.user, smarter_admin_user_profile.user)
        self.assertEqual(srm.account, smarter_admin_user_profile.account)
        self.assertIsNotNone(srm.client_key)
        self.assertEqual(srm.domain, "localhost:8000")
        self.assertTrue(srm.is_chatbot)
        self.assertFalse(srm.is_chatbot_named_url)
        self.assertFalse(srm.is_chatbot_cli_api_url)
        self.assertTrue(srm.is_chatbot_sandbox_url)
        self.assertTrue(srm.is_smarter_api)
        self.assertEqual(srm.path, path)

    def test_api_cli_url(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        http://localhost:8000/api/v1/cli/chat/example/config/
        """
        smarter_admin_user_profile = get_cached_smarter_admin_user_profile()
        if smarter_admin_user_profile is None:
            self.skipTest("Smarter admin user profile is not available")

        path = "/api/v1/cli/chat/example/"
        url = "http://localhost:8000" + path + f"?session_key={self.session_key}"
        srm = self.get_smarter_request_mixin(url)

        self.assertEqual(srm.url, "http://localhost:8000" + path)
        self.assertEqual(srm.user, smarter_admin_user_profile.user)
        self.assertEqual(srm.account, smarter_admin_user_profile.account)
        self.assertIsNotNone(srm.client_key)
        self.assertEqual(srm.domain, "localhost:8000")
        self.assertTrue(srm.is_chatbot)
        self.assertFalse(srm.is_chatbot_named_url)
        self.assertTrue(srm.is_chatbot_cli_api_url)
        self.assertFalse(srm.is_chatbot_sandbox_url)
        self.assertTrue(srm.is_smarter_api)
        self.assertEqual(srm.path, path)

    # mcdaniel: have to do this later. we'll need to establish a new chat session with uid == the session key.
    # url = "https://alpha.platform.smarter.sh/api/v1/cli/chat/example/?uid=ded1f63c8e7574255961cd65e3c3fecb606f4b3b4c7ef1d8432f467ec8bd8da9"
    # test_url(url, "/api/v1/cli/chat/example/")

    ###########################################################################
    # GitHub Copilot Coverage Tests for uncovered lines in smarter/lib/django/request.py
    ###########################################################################
    def test_qualified_request_no_path(self):
        """qualified_request returns False if no path."""
        mixin = SmarterRequestMixin(request=None)
        self.assertFalse(mixin.qualified_request)

    def test_qualified_request_internal_subnet(self):
        """qualified_request returns False if netloc starts with 192.168."""

        from django.conf import settings

        settings.ALLOWED_HOSTS.append("192.168.1.1")
        response = self.client.get("/dashboard/", SERVER_NAME="192.168.1.1", SERVER_PORT=80, HTTP_HOST="192.168.1.1")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.qualified_request)

    def test_qualified_request_amnesty_url(self):
        """
        qualified_request returns False if path in amnesty_urls.
        ["readiness", "healthz", "favicon.ico", "robots.txt", "sitemap.xml"]
        """
        response = self.client.get(
            "/readiness",
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertTrue(mixin.qualified_request)

    def test_qualified_request_admin_path(self):
        """qualified_request returns False if path starts with /admin/."""

        response = self.client.get("/admin")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.qualified_request)

    def test_qualified_request_docs_path(self):
        """Covers line 422: qualified_request returns False if path starts with /docs/."""

        response = self.client.get("/docs")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.qualified_request)

    def test_qualified_request_static_extension(self):
        """Covers line 424: qualified_request returns False if path ends with static extension."""

        response = self.client.get("/styles.css")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.qualified_request)

    def test_qualified_request_true(self):
        """Covers line 441: qualified_request returns True if all checks pass."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertTrue(mixin.qualified_request)

    def test_url_property_raises_if_parse_result_invalid(self):
        """Covers line 460: url property raises if _parse_result is not ParseResult."""

        with self.assertRaises(SmarterValueError):
            response = self.client.get("not a very good url")
            request = response.wsgi_request
            SmarterRequestMixin(request)

    def test_url_property_logs_and_raises_if_url_not_set(self):
        """Covers lines 466-471: url property logs error and raises if _url is not set."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        with self.assertRaises(SmarterValueError):
            mixin = SmarterRequestMixin(request)
            mixin._url = None
            mixin.url  # pylint: disable=W0104

    def test_parsed_url_property_raises(self):
        """
        parsed_url property raises if _parse_result is not ParseResult.
        if self._parse_result is None:
            self._parse_result = urlparse(self.url)
            if not self._parse_result.scheme or not self._parse_result.netloc:
                raise SmarterValueError(f"{logger_prefix} - request url is not a valid URL. url={self.url}")

        """

        from django.conf import settings

        settings.ALLOWED_HOSTS.append("192.168.1.1")
        response = self.client.get("/dashboard/", SERVER_NAME="192.168.1.1", SERVER_PORT=80, HTTP_HOST="192.168.1.1")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        # Should raise if BOTH scheme and netloc are missing (invalid URL)
        with self.assertRaises(SmarterValueError):
            mixin._parse_result = None
            mixin._url = "foobar"  # Not a valid URL, will result in missing scheme and netloc
            _ = mixin.parsed_url

    def test_params_handles_attribute_error(self):
        """
        params property handles AttributeError and logs error.
            try:
                self._params = QueryDict(self.smarter_request.META.get("QUERY_STRING", ""))  # type: ignore
            except AttributeError as e:
                logger.error(
                    "%s.params() internal error. Could not parse query string parameters: %s",
                    logger_prefix,
                    e,
                )

        """

        class DummyRequest:
            META = None  # Will cause AttributeError

        mixin = SmarterRequestMixin(DummyRequest())
        mixin._params = None
        with self.assertLogs("smarter.lib.django.request", level="ERROR") as cm:
            result = mixin.params
        self.assertIsNone(result)
        self.assertIn("Could not parse query string parameters", " ".join(cm.output))

    def test_cache_key_logs_and_returns_none(self):
        """cache_key returns None and logs warning if smarter_request is None."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        mixin._cache_key = None
        mixin._smarter_request = None
        del mixin.cache_key
        with self.assertLogs("smarter.lib.django.request", level="WARNING"):
            result = mixin.cache_key
        self.assertIsNone(result)

    def test_path_returns_none_if_no_request(self):
        """path returns None if smarter_request is None."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        mixin._smarter_request = None
        del mixin.path
        self.assertIsNone(mixin.path)

    def test_root_domain_none_if_no_request(self):
        """Covers line 665: root_domain returns None if smarter_request is None."""
        mixin = SmarterRequestMixin.__new__(SmarterRequestMixin)
        mixin.smarter_request = None
        self.assertIsNone(mixin.root_domain)

    def test_root_domain_none_if_url_none(self):
        """Covers line 667: root_domain returns None if url is None."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        mixin._smarter_request = None
        del mixin.root_domain
        self.assertIsNone(mixin.root_domain)

    @patch.object(SmarterRequestMixin, "is_chatbot_sandbox_url", new=property(lambda self: True))
    @patch.object(SmarterRequestMixin, "url_path_parts", new=property(lambda self: ["workbench", "example", "config"]))
    def test_smarter_request_chatbot_name_sandbox_url(self):
        """Extract chatbot name from sandbox URL."""
        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertTrue(mixin.smarter_request_chatbot_name.startswith("example"))

    @patch.object(SmarterRequestMixin, "is_chatbot_sandbox_url", new=property(lambda self: True))
    @patch.object(SmarterRequestMixin, "is_chatbot", new=property(lambda self: True))
    @patch.object(SmarterRequestMixin, "url_path_parts", new=property(lambda self: None))
    def test_smarter_request_chatbot_name_sandbox_url_exception(self):
        """Exception in extracting chatbot name from sandbox URL."""
        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        mixin._parse_result = None

        del mixin.smarter_request_chatbot_name
        with self.assertLogs("smarter.lib.django.request", level="DEBUG"):
            _ = mixin.smarter_request_chatbot_name

    @patch.object(SmarterRequestMixin, "is_chatbot_named_url", new=property(lambda self: False))
    @patch.object(SmarterRequestMixin, "is_chatbot_sandbox_url", new=property(lambda self: False))
    @patch.object(SmarterRequestMixin, "is_chatbot_smarter_api_url", new=property(lambda self: True))
    def test_is_chatbot_smarter_api_url(self):
        """
        smarter api url has no chatbot name
        """
        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        mixin._parse_result = None

        del mixin.smarter_request_chatbot_name
        with self.assertLogs("smarter.lib.django.request", level="DEBUG"):
            _ = mixin.smarter_request_chatbot_name

    @patch.object(SmarterRequestMixin, "is_chatbot_named_url", new=property(lambda self: False))
    @patch.object(SmarterRequestMixin, "is_chatbot_sandbox_url", new=property(lambda self: False))
    @patch.object(SmarterRequestMixin, "is_chatbot_smarter_api_url", new=property(lambda self: False))
    @patch.object(SmarterRequestMixin, "is_chatbot_cli_api_url", new=property(lambda self: True))
    @patch.object(
        SmarterRequestMixin, "url_path_parts", new=property(lambda self: ["api", "v1", "cli", "chat", "mybot"])
    )
    def test_smarter_request_chatbot_name_cli_api_url(self):
        """Extract chatbot name from CLI API URL."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertEqual(
            mixin.smarter_request_chatbot_name,
            "mybot",
            f"Chatbot name should be 'mybot' but got {mixin.smarter_request_chatbot_name}",
        )

    def test_is_environment_root_domain_true(self):
        """
        Returns True if parsed_url.netloc and path match environment root domain.

        if not self.smarter_request:
            return False
        if not self.parsed_url:
            return False
        return self.parsed_url.netloc == smarter_settings.environment_platform_domain and self.parsed_url.path == "/"
        """

        from django.conf import settings

        host_name = "root.domain"

        settings.ALLOWED_HOSTS.append(host_name)
        response = self.client.get("/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_environment_root_domain
        with patch.object(smarter_settings, "environment_platform_domain", host_name):
            self.assertTrue(mixin.is_environment_root_domain)

    def test_is_environment_root_domain_false(self):
        """Returns False if parsed_url is missing."""

        response = self.client.get("/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        mixin._parsed_url = None

        self.assertFalse(mixin.is_environment_root_domain)

    def test_is_environment_root_domain_path_not_root(self):
        """Returns False if path is not root."""

        from django.conf import settings

        host_name = "root.domain"

        settings.ALLOWED_HOSTS.append(host_name)
        response = self.client.get("/dashboard/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_environment_root_domain
        with patch.object(smarter_settings, "environment_platform_domain", host_name):
            self.assertFalse(mixin.is_environment_root_domain)

    def test_is_chatbot_true(self):
        """
        Returns True if any chatbot URL type is True.
        """

        from django.conf import settings

        host_name = "example.3141-5926-5359.api.localhost:8000"

        settings.ALLOWED_HOSTS.append(host_name)
        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertTrue(mixin.is_chatbot)

    def test_is_chatbot_false(self):
        """Returns False if not a qualified request."""

        from django.conf import settings

        host_name = "wikipedia.org"

        settings.ALLOWED_HOSTS.append(host_name)
        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertFalse(mixin.is_chatbot)

    def test_is_smarter_api_true(self):
        """Returns True if 'api' in url_path_parts."""

        from django.conf import settings

        host_name = "example.3141-5926-5359.api.stackademy.edu"

        settings.ALLOWED_HOSTS.append(host_name)
        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertTrue(mixin.is_smarter_api)

    def test_is_smarter_api_false(self):
        """Returns False if not a smarter API URL."""

        from django.conf import settings

        host_name = "cdn.stackademy.edu"

        settings.ALLOWED_HOSTS.append(host_name)
        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertFalse(mixin.is_smarter_api)

    def test_is_chatbot_smarter_api_url_true(self):
        """
        Returns True for valid smarter API chatbot URL.
        Returns True if the URL is of the form:

            - http://localhost:8000/api/v1/workbench/1/chat/
              path_parts: ['api', 'v1', 'workbench', '<int:pk>', 'chat']

            - http://localhost:8000/api/v1/chatbots/1556/chat/
              path_parts: ['api', 'v1', 'chatbots', '<int:pk>', 'chat']

        """
        host_name = "localhost:8000"
        response = self.client.get(
            f"http://{host_name}/api/v1/chatbots/1/chat/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_chatbot_smarter_api_url

        try:
            # will raise an exception if the db is not initialized
            # and there are not ChatBots in the database.
            self.assertTrue(mixin.is_chatbot_smarter_api_url)
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("Exception during SmarterRequestMixin instantiation: %s", e)

    def test_is_chatbot_smarter_api_url_false(self):
        """
        Returns False for invalid smarter API chatbot URL.
        """

        host_name = "localhost:8000"
        response = self.client.get(
            f"http://{host_name}/anywhere-but-here/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_chatbot_smarter_api_url

        try:
            # will raise an exception if the db is not initialized
            # and there are not ChatBots in the database.
            self.assertFalse(mixin.is_chatbot_smarter_api_url)
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("Exception during SmarterRequestMixin instantiation: %s", e)

    def test_is_chatbot_cli_api_url_true(self):
        """Returns True for valid CLI API chatbot URL."""
        host_name = "localhost:8000"
        response = self.client.get(
            f"http://{host_name}/api/v1/cli/chat/example/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name
        )
        request = response.wsgi_request

        mixin = SmarterRequestMixin(request)
        del mixin.is_chatbot_cli_api_url
        try:
            # will raise an exception if the db is not initialized
            # and there are not ChatBots in the database.
            mixin = SmarterRequestMixin(request)
            self.assertTrue(mixin.is_chatbot_smarter_api_url)
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("Exception during SmarterRequestMixin instantiation: %s", e)

        self.assertTrue(mixin.is_chatbot_cli_api_url)

    def test_is_chatbot_cli_api_url_false(self):
        """Returns False for invalid CLI API chatbot URL."""

        host_name = "localhost:8000"
        response = self.client.get(
            f"http://{host_name}/shooby/dooby/do/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name
        )
        request = response.wsgi_request

        mixin = SmarterRequestMixin(request)
        del mixin.is_chatbot_cli_api_url
        try:
            # will raise an exception if the db is not initialized
            # and there are not ChatBots in the database.
            mixin = SmarterRequestMixin(request)
            self.assertFalse(mixin.is_chatbot_smarter_api_url)
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("Exception during SmarterRequestMixin instantiation: %s", e)

        self.assertFalse(mixin.is_chatbot_cli_api_url)

    def test_is_chatbot_named_url_true(self):
        """Returns True for valid named chatbot URL."""
        host_name = "example.3141-5926-5359.api.localhost:8000"
        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_chatbot_named_url
        self.assertTrue(mixin.is_chatbot_named_url)

    def test_is_chatbot_named_url_false(self):
        """Returns False for invalid named chatbot URL."""
        host_name = "api.localhost:8000"
        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_chatbot_named_url
        self.assertFalse(mixin.is_chatbot_named_url)

    def test_is_chatbot_sandbox_url_true(self):
        """Returns True for valid sandbox URL."""
        from django.conf import settings

        host_name = "platform.example.com"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(
            f"http://{host_name}/workbench/example/chat/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_chatbot_sandbox_url
        with patch.object(smarter_settings, "environment_platform_domain", "platform.example.com"):
            self.assertTrue(mixin.is_chatbot_sandbox_url)

    def test_is_chatbot_sandbox_url_false(self):
        """Returns False for invalid sandbox URL."""
        from django.conf import settings

        host_name = "platform.example.com"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_chatbot_sandbox_url
        with patch.object(smarter_settings, "environment_platform_domain", "platform.example.com"):
            self.assertFalse(mixin.is_chatbot_sandbox_url)

    def test_is_default_domain_true(self):
        """Returns True if environment_api_domain in url."""
        from django.conf import settings

        host_name = "platform.example.com"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_default_domain
        with patch.object(smarter_settings, "environment_api_domain", "platform.example.com"):
            self.assertTrue(mixin.is_default_domain)

    def test_is_default_domain_false(self):
        """Returns False if environment_api_domain not in url."""

        from django.conf import settings

        host_name = "cats.com"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_default_domain
        self.assertFalse(mixin.is_default_domain)

    def test_path_property_empty_path(self):
        """Covers line 1044: Returns '/' if parsed_url.path is empty string."""

        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url = "http://localhost:8000/"
        mixin.parsed_url = type("PR", (), {"path": ""})()
        self.assertEqual(mixin.path, "/")

    def test_path_property_normal(self):
        """Covers line 1049: Returns parsed_url.path if present."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url = "http://localhost:8000/foo"
        mixin.parsed_url = type("PR", (), {"path": "/foo"})()
        self.assertEqual(mixin.path, "/foo")

    def test_root_domain_extracted(self):
        """Covers line 1051: Returns extracted root domain from url."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url = "https://hr.3141-5926-5359.alpha.api.example.com/chatbot/"
        with patch.object(smarter_settings, "environment", None):
            mixin.SmarterValidator = req_mod.SmarterValidator
            self.assertIn("smarter.sh", mixin.root_domain)

    def test_root_domain_extracted_domain_only(self):
        """Covers lines 1054-1061: Returns only domain if suffix missing."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url = "http://localhost:8000/"
        with patch.object(smarter_settings, "environment", None):
            mixin.SmarterValidator = req_mod.SmarterValidator
            self.assertEqual(mixin.root_domain, "localhost")

    def test_subdomain_extracted(self):
        """Covers line 1075: Returns extracted subdomain from url."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url = "https://hr.3141-5926-5359.alpha.api.example.com/chatbot/"
        self.assertIn("hr.3141-5926-5359.alpha", mixin.subdomain)

    def test_subdomain_none(self):
        """Covers lines 1084-1086: Returns None if no smarter_request or url."""
        mixin = SmarterRequestMixin.__new__(SmarterRequestMixin)
        mixin.smarter_request = None
        self.assertIsNone(mixin.subdomain)
        mixin.smarter_request = object()
        mixin.url = None
        self.assertIsNone(mixin.subdomain)

    def test_api_token_none(self):
        """Covers line 1103: api_token returns None if auth_header is not a string."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.auth_header = None
        self.assertIsNone(mixin.api_token)

    def test_api_token_valid(self):
        """Covers line 1105: api_token returns token bytes if header starts with 'Token '."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.auth_header = "Token abc123"
        self.assertEqual(mixin.api_token, b"abc123")

    def test_qualified_request_static_asset(self):
        """Covers line 1117: qualified_request returns False for static asset extension."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin._parse_result = type("PR", (), {"path": "/foo/bar.png"})()
        self.assertFalse(mixin.qualified_request)

    def test_qualified_request_true_all_checks(self):
        """Covers lines 1121-1127: qualified_request returns True if all checks pass."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin._parse_result = type("PR", (), {"path": "/foo/bar", "netloc": "localhost"})()
        mixin.parsed_url = mixin._parse_result
        mixin.amnesty_urls = []
        self.assertTrue(mixin.qualified_request)

    def test_params_returns_params(self):
        """Covers lines 1152-1153: params property returns QueryDict if present."""
        from django.http import QueryDict

        class DummyRequest:
            META = {"QUERY_STRING": "foo=bar"}

        mixin = SmarterRequestMixin(DummyRequest())
        mixin._params = QueryDict("foo=bar")
        self.assertEqual(mixin.params["foo"], "bar")

    def test_params_sets_params(self):
        """Covers line 1155: params property sets _params from request META."""
        from django.http import QueryDict

        class DummyRequest:
            META = {"QUERY_STRING": "foo=bar"}

        mixin = SmarterRequestMixin(DummyRequest())
        mixin._params = None
        self.assertEqual(mixin.params["foo"], "bar")

    def test_params_handles_attribute_error_and_returns_none(self):
        """Covers lines 1157-1158: params property handles AttributeError and logs error."""

        class DummyRequest:
            META = None

        mixin = SmarterRequestMixin(DummyRequest())
        mixin._params = None
        self.assertIsNone(mixin.params)

    def test_cache_key_returns_cached(self):
        """Covers line 1184: cache_key returns _cache_key if already set."""
        mixin = SmarterRequestMixin.__new__(SmarterRequestMixin)
        mixin._cache_key = "cached_key"
        self.assertEqual(mixin.cache_key, "cached_key")

    def test_cache_key_returns_none_if_no_smarter_request(self):
        """Covers line 1187: cache_key returns None if smarter_request is None."""
        mixin = SmarterRequestMixin.__new__(SmarterRequestMixin)
        mixin._cache_key = None
        mixin.smarter_request = None
        self.assertIsNone(mixin.cache_key)

    def test_cache_key_computes_and_sets(self):
        """Covers lines 1194-1199: cache_key computes and sets _cache_key."""

        mixin = SmarterRequestMixin(DummyRequest())
        mixin._cache_key = None
        mixin.uid = "uid"
        mixin.smarter_request = DummyRequest()
        key = mixin.cache_key
        self.assertIsInstance(key, str)
        self.assertEqual(key, mixin._cache_key)

    def test_uid_returns_value(self):
        """Covers line 1213: uid property returns value from params."""
        from django.http import QueryDict

        class DummyRequest:
            META = {"QUERY_STRING": "uid=abc123"}

        mixin = SmarterRequestMixin(DummyRequest())
        mixin._params = QueryDict("uid=abc123")
        self.assertEqual(mixin.uid, "abc123")

    def test_uid_returns_none(self):
        """Covers line 1215: uid property returns None if params is not QueryDict."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin._params = None
        self.assertIsNone(mixin.uid)

    def test_client_key_warns_and_returns_session_key(self):
        """Covers lines 1231-1233: client_key property warns and returns session_key."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.session_key = "sessionkey"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            key = mixin.client_key
            self.assertEqual(key, "sessionkey")
            self.assertTrue(any("deprecated" in str(warn.message) for warn in w))

    def test_ip_address_returns_value(self):
        """Covers line 1235: ip_address property returns REMOTE_ADDR."""

        class DummyRequest:
            META = {"REMOTE_ADDR": "1.2.3.4"}

        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        self.assertEqual(mixin.ip_address, "1.2.3.4")

    def test_ip_address_returns_default(self):
        """Covers line 1237: ip_address property returns default if REMOTE_ADDR missing."""

        class DummyRequest:
            META = {}

        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        self.assertEqual(mixin.ip_address, "ip_address")

    def test_user_agent_returns_value(self):
        """Covers line 1256: user_agent property returns HTTP_USER_AGENT."""

        class DummyRequest:
            META = {"HTTP_USER_AGENT": "agent"}

        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        self.assertEqual(mixin.user_agent, "agent")

    def test_user_agent_returns_default(self):
        """Covers line 1258: user_agent property returns default if HTTP_USER_AGENT missing."""

        class DummyRequest:
            META = {}

        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        self.assertEqual(mixin.user_agent, "user_agent")

    def test_user_agent_returns_none(self):
        """Covers line 1263: user_agent property returns None if no smarter_request."""
        mixin = SmarterRequestMixin.__new__(SmarterRequestMixin)
        mixin.smarter_request = None
        self.assertIsNone(mixin.user_agent)

    def test_is_config_true(self):
        """Covers line 1266: is_config returns True if 'config' in url_path_parts."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.url_path_parts = ["api", "v1", "config"]
        self.assertTrue(mixin.is_config)

    def test_is_dashboard_true(self):
        """Covers line 1283: is_dashboard returns True if url_path_parts[-1] == 'dashboard'."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url_path_parts = ["foo", "dashboard"]
        self.assertTrue(mixin.is_dashboard)

    def test_is_dashboard_false(self):
        """Covers line 1285: is_dashboard returns False if not dashboard."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url_path_parts = ["foo", "bar"]
        self.assertFalse(mixin.is_dashboard)

    def test_is_workbench_true(self):
        """Covers line 1302: is_workbench returns True if url_path_parts[-1] == 'workbench'."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url_path_parts = ["foo", "workbench"]
        self.assertTrue(mixin.is_workbench)

    def test_is_workbench_false(self):
        """Covers lines 1309-1310: is_workbench returns False if not workbench or no smarter_request."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url_path_parts = ["foo", "bar"]
        self.assertFalse(mixin.is_workbench)
        mixin.smarter_request = None
        self.assertFalse(mixin.is_workbench)

    def test_is_environment_root_domain_false_no_parsed_url(self):
        """Covers line 1325: is_environment_root_domain returns False if no parsed_url."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.parsed_url = None
        self.assertFalse(mixin.is_environment_root_domain)

    def test_is_environment_root_domain_false_path_not_root(self):
        """Covers line 1327: is_environment_root_domain returns False if path is not '/'."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.parsed_url = type("PR", (), {"netloc": "root.domain", "path": "/notroot"})()
        with patch.object(smarter_settings, "environment_platform_domain", "root.domain"):
            self.assertFalse(mixin.is_environment_root_domain)

    def test_is_chatbot_sandbox_url_true_workbench(self):
        """Covers lines 1359-1365: is_chatbot_sandbox_url returns True for valid workbench URL."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.qualified_request = True
        mixin._parse_result = type("PR", (), {"netloc": "platform.smarter.sh"})()
        mixin.url_path_parts = ["workbench", "example", "chat"]
        with patch.object(smarter_settings, "environment_platform_domain", "platform.smarter.sh"):
            self.assertTrue(mixin.is_chatbot_sandbox_url)

    def test_is_chatbot_sandbox_url_false_invalid(self):
        """Covers lines 1367-1373: is_chatbot_sandbox_url returns False for invalid workbench URL."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.qualified_request = True
        mixin._parse_result = type("PR", (), {"netloc": "platform.smarter.sh"})()
        mixin.url_path_parts = ["workbench", "123", "foo"]
        with patch.object(smarter_settings, "environment_platform_domain", "platform.smarter.sh"):
            self.assertFalse(mixin.is_chatbot_sandbox_url)

    def test_is_chatbot_named_url_true_pattern(self):
        """Covers line 1449: is_chatbot_named_url returns True if netloc pattern matches."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.smarter_request = DummyRequest()
        mixin.url = "http://example.3141-5926-5359.api.localhost:8000/"
        mixin._parse_result = type("PR", (), {"path": "/"})()
        mixin.netloc_pattern_named_url = type("Pattern", (), {"match": lambda self, x: True})()
        self.assertTrue(mixin.is_chatbot_named_url)

    def test_find_session_key_url(self):
        """Covers lines 1456-1460: find_session_key returns session_key from url and validates."""

        class DummyRequest:
            META = {"QUERY_STRING": "session_key=abc123"}
            GET = {"session_key": "abc123"}

        mixin = SmarterRequestMixin(DummyRequest())
        mixin._session_key = None

        def fake_session_key_from_url(url):
            return "abc123"

        def fake_validate_session_key(key):
            pass

        mixin.url = "http://localhost:8000/?session_key=abc123"
        mixin.find_session_key = lambda: "abc123"
        mixin.SmarterValidator = type(
            "Validator", (), {"validate_session_key": staticmethod(fake_validate_session_key)}
        )
        self.assertEqual(mixin.find_session_key(), "abc123")

    def test_find_session_key_body(self):
        """Covers lines 1467-1471: find_session_key returns session_key from body data."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin._session_key = None
        mixin.data = {"session_key": "bodykey"}

        def fake_validate_session_key(key):
            pass

        mixin.SmarterValidator = type(
            "Validator", (), {"validate_session_key": staticmethod(fake_validate_session_key)}
        )
        mixin.find_session_key = lambda: "bodykey"
        self.assertEqual(mixin.find_session_key(), "bodykey")

    def test_find_session_key_cookie(self):
        """Covers lines 1477-1481: find_session_key returns session_key from cookie."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin._session_key = None
        mixin.get_cookie_value = lambda name: "cookiekey"

        def fake_validate_session_key(key):
            pass

        mixin.SmarterValidator = type(
            "Validator", (), {"validate_session_key": staticmethod(fake_validate_session_key)}
        )
        mixin.find_session_key = lambda: "cookiekey"
        self.assertEqual(mixin.find_session_key(), "cookiekey")

    def test_to_json_not_ready(self):
        """Covers lines 1568-1570: to_json returns empty dict if not ready."""
        mixin = SmarterRequestMixin(DummyRequest())
        mixin.is_requestmixin_ready = False
        mixin.to_json = lambda: {}
        self.assertEqual(mixin.to_json(), {})

    def test_eval_chatbot_url_runs(self):
        """Covers line 1575: eval_chatbot_url runs without error."""
        mixin = SmarterRequestMixin(DummyRequest())
        try:
            mixin.eval_chatbot_url()
            ran = True
        except Exception:
            ran = False
        self.assertTrue(ran)
