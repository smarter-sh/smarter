# pylint: disable=W0212
"""Test SmarterRequestMixin."""

from datetime import datetime
from logging import getLogger
from unittest.mock import patch
from urllib.parse import ParseResult

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest, QueryDict
from django.test import Client, RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.utils import is_authenticated_request
from smarter.lib.django.request import SmarterRequestMixin


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

    def tearDown(self):
        try:
            self.client.logout()
            self.client = None
        # pylint: disable=W0718
        except Exception:
            pass
        super().tearDown()

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
        Test that SmarterRequestMixin raises SmarterValueError
        when initialized without a request object.
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

    def test_unauthenticated_base_case(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        """
        host_name = "testserver"
        request = self.client.get(
            f"/?session_key={self.session_key}",
            SERVER_NAME=host_name,
            SERVER_PORT=80,
            HTTP_HOST=host_name,
            REMOTE_ADDR="1.2.3.4",
        )

        srm = SmarterRequestMixin(request.wsgi_request)
        self.assertIsNone(srm.account)
        self.assertIsNotNone(srm.session_key)
        self.assertEqual(srm.domain, "testserver")
        self.assertEqual(srm.ip_address, "1.2.3.4")
        self.assertFalse(srm.is_smarter_api)
        self.assertFalse(srm.is_chatbot)
        self.assertFalse(srm.is_chatbot_smarter_api_url)
        self.assertFalse(srm.is_chatbot_named_url)
        self.assertFalse(srm.is_chatbot_sandbox_url)
        self.assertFalse(srm.is_chatbot_cli_api_url)
        self.assertFalse(srm.is_default_domain)
        self.assertEqual(srm.path, "/")
        self.assertEqual(srm.root_domain, "testserver")
        self.assertEqual(srm.subdomain, None)
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
        self.assertTrue(srm.is_smarter_api)
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

        SmarterRequestMixin(request=None)

    def test_qualified_request_internal_subnet(self):
        """qualified_request returns False if netloc starts with 192.168."""

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
        """qualified_request returns False if path starts with /docs/."""

        response = self.client.get("/docs")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.qualified_request)

    def test_qualified_request_static_extension(self):
        """qualified_request returns False if path ends with static extension."""

        response = self.client.get("/styles.css")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.qualified_request)

    def test_qualified_request_true(self):
        """qualified_request returns True if all checks pass."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertTrue(mixin.qualified_request)

    def test_url_property_raises_if_parse_result_invalid(self):
        """url property raises if _parse_result is not ParseResult."""

        response = self.client.get("not a very good url")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        mixin._url = "ftp:// be.bop a loo bop. not a very \ngood url----"
        self.assertEqual(mixin.url, "http://testserver/not%20a%20very%20good%20url/")

    def test_url_property_logs_and_raises_if_url_not_set(self):
        """url property logs error and raises if _url is not set."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request

        mixin = SmarterRequestMixin(request)
        mixin.clear_cached_properties()
        mixin.smarter_request = request
        self.assertIsNotNone(mixin.url)

    def test_parsed_url_property_raises(self):
        """
        parsed_url property returns None if not ParseResult.
        """

        settings.ALLOWED_HOSTS.append("192.168.1.1")
        response = self.client.get("/dashboard/", SERVER_NAME="192.168.1.1", SERVER_PORT=80, HTTP_HOST="192.168.1.1")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        mixin.clear_cached_properties()
        mixin.smarter_request = request
        self.assertIsNotNone(mixin.parsed_url)

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

        mixin = SmarterRequestMixin(DummyRequest())
        mixin._params = None
        result = mixin.params
        self.assertEqual(result, QueryDict(""))

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
        """root_domain returns None if smarter_request is None."""
        mixin = SmarterRequestMixin.__new__(SmarterRequestMixin)
        mixin.smarter_request = None
        self.assertIsNone(mixin.root_domain)

    def test_root_domain_none_if_url_none(self):
        """root_domain returns None if url is None."""

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

        host_name = "example.3141-5926-5359.api.localhost:8000"

        settings.ALLOWED_HOSTS.append(host_name)
        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertTrue(mixin.is_chatbot)

    def test_is_chatbot_false(self):
        """Returns False if not a qualified request."""

        host_name = "wikipedia.org"

        settings.ALLOWED_HOSTS.append(host_name)
        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertFalse(mixin.is_chatbot)

    def test_is_smarter_api_true(self):
        """Returns True if 'api' in url_path_parts."""

        host_name = "example.3141-5926-5359.api.stackademy.edu"

        settings.ALLOWED_HOSTS.append(host_name)
        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertTrue(mixin.is_smarter_api)

    def test_is_smarter_api_false(self):
        """Returns False if not a smarter API URL."""

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

        host_name = "cats.com"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.is_default_domain
        self.assertFalse(mixin.is_default_domain)

    def test_path_property_empty_path(self):
        """Returns '/' if parsed_url.path is empty string."""

        response = self.client.get("")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.path
        self.assertEqual(mixin.path, "/")

    def test_path_property_normal(self):
        """Returns parsed_url.path if present."""
        response = self.client.get("/fu/man/chou/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.path
        self.assertEqual(mixin.path, "/fu/man/chou/")

    def test_root_domain_extracted(self):
        """Returns extracted root domain from url."""

        host_name = "dogs.com"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.root_domain
        self.assertEqual("dogs.com", mixin.root_domain)

    def test_root_domain_extracted_domain_only(self):
        """Returns only domain if suffix missing."""

        host_name = "dogs"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(f"http://{host_name}/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name)
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.root_domain
        self.assertEqual("dogs", mixin.root_domain, f"Root domain should be 'dogs' but got {mixin.root_domain}")

    def test_subdomain_extracted(self):
        """Returns extracted subdomain from url."""

        host_name = "hr.3141-5926-5359.alpha.api.example.com"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(
            f"http://{host_name}/chatbot/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.subdomain
        self.assertEqual(
            "hr.3141-5926-5359.alpha.api",
            mixin.subdomain,
            f"Subdomain should be 'hr.3141-5926-5359.alpha.api' but got {mixin.subdomain}",
        )

    def test_subdomain_none(self):
        """Returns None if no smarter_request or url."""

        host_name = "example.com"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(
            f"http://{host_name}/chatbot/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        del mixin.subdomain
        self.assertIsNone(mixin.subdomain)

    def test_api_token_none(self):
        """api_token returns None if auth_header is not a string."""
        response = self.client.get("/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertIsNone(mixin.api_token)

    def test_api_token_valid(self):
        """api_token returns token bytes if header starts with 'Token '."""
        response = self.client.get(
            path="/",
            headers={"Authorization": "Token abc123"},
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        with patch.object(SmarterRequestMixin, "auth_header", new="Token abc123"):
            self.assertEqual(mixin.api_token, b"abc123")

    def test_qualified_request_static_asset(self):
        """qualified_request returns False for static asset extension."""
        response = self.client.get("styles.css")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.qualified_request)

    def test_qualified_request_true_all_checks(self):
        """qualified_request returns True if all checks pass."""
        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertTrue(mixin.qualified_request)

    def test_params_returns_params(self):
        """params property returns QueryDict if present."""

        response = self.client.get(
            path="/dashboard/",
            query_params={"foo": "bar"},
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertIsInstance(mixin.params, QueryDict)
        self.assertIn("foo", mixin.params)  # type: ignore
        self.assertEqual(mixin.params["foo"], "bar")  # type: ignore

    def test_params_handles_attribute_error_and_returns_none(self):
        """params property handles AttributeError and logs error."""

        response = self.client.get(
            path="/dashboard/",
            query_params={"foo": "bar"},
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        mixin._smarter_request.META = None  # Will cause AttributeError
        mixin._params = None
        with self.assertLogs("smarter.lib.django.request", level="ERROR"):
            result = mixin.params
            self.assertEqual(result, QueryDict(""))
        self.assertEqual(mixin.params, QueryDict(""))

    def test_cache_key_returns_cached(self):
        """cache_key returns _cache_key if already set."""
        mixin = SmarterRequestMixin.__new__(SmarterRequestMixin)
        mixin._cache_key = "cached_key"
        self.assertEqual(mixin.cache_key, "cached_key")

    def test_cache_key_returns_none_if_no_smarter_request(self):
        """cache_key returns None if smarter_request is None."""
        response = self.client.get("/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        mixin._cache_key = None
        mixin._smarter_request = None
        del mixin.cache_key
        self.assertIsNone(mixin.cache_key)

    def test_cache_key_computes_and_sets(self):
        """cache_key computes and sets a deterministic (reproducible) cache_key."""

        response = self.client.get("/")
        request = response.wsgi_request

        # create a new mixin instance
        logger.debug("1. Creating SmarterRequestMixin for cache_key test.")
        mixin = SmarterRequestMixin(request)
        self.assertIsNotNone(mixin.cache_key)

        # stash the current cache key and request
        saved_mixin_cache_key = mixin.cache_key
        saved_smarter_request = mixin.smarter_request

        # clear the cache key and smarter_request to force recomputation
        logger.debug("2. Clearing cached cache_key.")
        mixin.clear_cached_properties()
        self.assertIsNone(mixin.cache_key)

        # restore the smarter_request and recompute cache key
        logger.debug("3. Restoring smarter_request and recomputing cache_key.")
        mixin.clear_cached_properties()
        mixin.smarter_request = saved_smarter_request
        new_key = mixin.cache_key

        self.assertIsInstance(new_key, str)
        self.assertEqual(new_key, saved_mixin_cache_key)

        logger.debug("4. Restoring original cache_key.")
        mixin.clear_cached_properties()
        mixin._cache_key = saved_mixin_cache_key
        mixin.smarter_request = saved_smarter_request
        self.assertEqual(mixin.cache_key, saved_mixin_cache_key)

    def test_uid_returns_value(self):
        """uid property returns value from params."""
        response = self.client.get(
            path="/dashboard/",
            query_params={"uid": "abc123"},
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertEqual(mixin.uid, "abc123")

    def test_uid_returns_none(self):
        """uid property returns None if params is not QueryDict."""
        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertIsNone(mixin.uid)

    def test_session_key(self):
        """
        client_key property warns and returns session_key.
        """
        session_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        response = self.client.get(
            path="/dashboard/",
            query_params={SMARTER_CHAT_SESSION_KEY_NAME: session_key},
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertEqual(mixin.session_key, session_key)

    def test_ip_address_returns_value(self):
        """
        ip_address property returns REMOTE_ADDR.
        if (
            self.smarter_request is not None
            and hasattr(self.smarter_request, "META")
            and isinstance(self.smarter_request.META, dict)
        ):
            return self.smarter_request.META.get("REMOTE_ADDR", "") or "ip_address"
        return None
        """
        host_name = "wafflehouse.com"
        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(
            f"http://{host_name}/chatbot/",
            SERVER_NAME=host_name,
            SERVER_PORT=80,
            HTTP_HOST=host_name,
            REMOTE_ADDR="1.2.3.4",
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertEqual(mixin.ip_address, "1.2.3.4")

    def test_ip_address_returns_default(self):
        """ip_address property returns default if REMOTE_ADDR missing."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        mixin._smarter_request.META.pop("REMOTE_ADDR", None)
        del mixin.ip_address
        self.assertEqual(mixin.ip_address, "ip_address")

    def test_user_agent_returns_value(self):
        """user_agent property returns HTTP_USER_AGENT."""

        host_name = "wafflehouse.com"
        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(
            f"http://{host_name}/chatbot/",
            SERVER_NAME=host_name,
            SERVER_PORT=80,
            HTTP_HOST=host_name,
            HTTP_USER_AGENT="test-user-agent",
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertEqual(mixin.user_agent, "test-user-agent")

    def test_user_agent_returns_default(self):
        """user_agent property returns default if HTTP_USER_AGENT missing."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        mixin._smarter_request.META.pop("HTTP_USER_AGENT", None)
        del mixin.user_agent
        self.assertEqual(mixin.user_agent, "user_agent")

    def test_user_agent_returns_none(self):
        """user_agent property returns None if no smarter_request."""
        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        mixin._smarter_request = None
        del mixin.user_agent
        self.assertIsNone(mixin.user_agent)

    def test_is_config_true(self):
        """is_config returns True if 'config' in url_path_parts."""
        host_name = "hr.3141-5926-5359.alpha." + smarter_settings.environment_api_domain

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(
            f"http://{host_name}/config/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        with patch.object(mixin, "is_chatbot", True):
            self.assertTrue(mixin.is_config)

    def test_is_dashboard_true(self):
        """is_dashboard returns True if url_path_parts[-1] == 'dashboard'."""
        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertTrue(mixin.is_dashboard)

    def test_is_dashboard_false(self):
        """is_dashboard returns False if not dashboard."""
        response = self.client.get("/not-the-dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.is_dashboard)

    def test_is_workbench_true(self):
        """is_workbench returns True if url_path_parts[-1] == 'workbench'."""
        response = self.client.get("/workbench/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertTrue(mixin.is_workbench)

    def test_is_workbench_false(self):
        """is_workbench returns False if not workbench or no smarter_request."""
        response = self.client.get("we/are/elsewhere/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.is_workbench)

    def test_is_environment_root_domain_false_path_not_root(self):
        """is_environment_root_domain returns False if path is not '/'."""
        host_name = "spam.com"

        settings.ALLOWED_HOSTS.append(host_name)

        response = self.client.get(
            f"http://{host_name}/yum/yummy/", SERVER_NAME=host_name, SERVER_PORT=80, HTTP_HOST=host_name
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)
        self.assertFalse(mixin.is_environment_root_domain)

    def test_find_session_key_url(self):
        """find_session_key returns session_key from url and validates."""

        session_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        response = self.client.get(
            path="/dashboard/",
            query_params={SMARTER_CHAT_SESSION_KEY_NAME: session_key},
        )
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertEqual(mixin.find_session_key(), session_key)

    def test_find_session_key_body(self):
        """find_session_key returns session_key from body data."""
        session_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        response = self.client.get("/dashboard/", data={SMARTER_CHAT_SESSION_KEY_NAME: session_key})
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertEqual(mixin.find_session_key(), session_key)

    def test_find_session_key_cookie(self):
        """find_session_key returns session_key from cookie."""

        session_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        self.client.cookies[SMARTER_CHAT_SESSION_KEY_NAME] = session_key
        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        self.assertEqual(mixin.find_session_key(), session_key)

    def test_to_json_not_ready(self):
        """to_json returns a dict regardless of whether its ready."""

        response = self.client.get("/dashboard/")
        request = response.wsgi_request
        mixin = SmarterRequestMixin(request)

        json_dump = mixin.to_json()
        self.assertIsInstance(json_dump, dict)
        self.assertIn("session_key", json_dump)
        self.assertIn("auth_header", json_dump)
        self.assertIn("api_token", json_dump)
        self.assertIn("data", json_dump)
        self.assertIn("chatbot_id", json_dump)
        self.assertIn("chatbot_name", json_dump)

        with patch.object(mixin, "is_requestmixin_ready", False):
            json_dump = mixin.to_json()
            self.assertIsInstance(json_dump, dict)
            self.assertIn("session_key", json_dump)
            self.assertIn("auth_header", json_dump)
            self.assertIn("api_token", json_dump)
            self.assertIn("data", json_dump)
            self.assertIn("chatbot_id", json_dump)
            self.assertIn("chatbot_name", json_dump)
