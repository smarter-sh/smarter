"""Test SmarterRequestMixin."""

from datetime import datetime
from logging import getLogger
from urllib.parse import ParseResult

from django.contrib.auth import authenticate
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.request import SmarterRequestMixin


SMARTER_DEV_ADMIN_PASSWORD = "smarter"
logger = getLogger(__name__)


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
    - https://hr.smarter.querium.com/

    """

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.wsgi_request_factory = RequestFactory()
        self.session_key = "1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a"

    def tearDown(self):
        try:
            self.client.logout()
            self.client = None
            self.wsgi_request_factory = None
        # pylint: disable=W0718
        except Exception:
            pass

    def get_smarter_request_mixin(self, url: str) -> SmarterRequestMixin:
        request_factory = RequestFactory()
        request = request_factory.get(url, SERVER_NAME="localhost:8000")
        smarter_admin_user_profile = get_cached_smarter_admin_user_profile()
        user = authenticate(username=smarter_admin_user_profile.user.username, password=SMARTER_DEV_ADMIN_PASSWORD)
        if user is None:
            self.fail("Authentication failed")
        request.user = user
        middleware = SessionMiddleware(lambda request: None)
        middleware.process_request(request)
        request.session.save()

        return SmarterRequestMixin(request)

    def test_init_without_request_object(self):
        """
        Test that SmarterRequestMixin doesn't identify any kind of resource nor api.
        """
        with self.assertRaises((SmarterValueError, TypeError)):
            SmarterRequestMixin(request=None)

    def test_unauthenticated_instantiation(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        """
        request = self.wsgi_request_factory.get("/")

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

    def test_request_object_is_readonly(self):
        """
        Test that SmarterRequestMixin request object is read-only.
        """
        self.client.login(username=self.admin_user.username, password="12345")
        response = self.client.get("/")
        request = response.wsgi_request

        srm = SmarterRequestMixin(request)
        with self.assertRaises(AttributeError):
            srm.smarter_request = None

    def test_unauthenticated_base_case(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        """
        request = self.wsgi_request_factory.get(f"/?session_key={self.session_key}", SERVER_NAME="testserver")
        srm = SmarterRequestMixin(request)
        self.assertIsNone(srm.account)
        self.assertIsNone(srm.session_key)
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
        self.assertEqual(request.user, smarter_admin_user_profile.user)
        self.assertEqual(url, request.build_absolute_uri())
        if not request.user.is_authenticated:
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
        self.assertIsNone(srm.session_key)
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
        self.assertIsNone(srm.client_key)
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
        self.assertIsNone(srm.client_key)
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
        self.assertIsNone(srm.client_key)
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
