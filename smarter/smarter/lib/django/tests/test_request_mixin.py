"""Test SmarterRequestMixin."""

import unittest
import uuid
from datetime import datetime
from urllib.parse import ParseResult

from django.contrib.auth.models import User
from django.test import Client, RequestFactory

from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.django.validators import SmarterValueError


SMARTER_DEV_ADMIN_PASSWORD = "smarter"


class TestSmarterRequestMixin(unittest.TestCase):
    """
    Test SmarterRequestMixin.
    example urls:
    - http://testserver
    - http://localhost:8000/
    - http://localhost:8000/docs/
    - http://localhost:8000/dashboard/
    - https://alpha.platform.smarter.sh/api/v1/chatbots/1/chatbot/
    - http://example.com/contact/
    - http://localhost:8000/chatbots/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/
    - https://hr.3141-5926-5359.alpha.api.smarter.sh/config/?session_key=38486326c21ef4bcb7e7bc305bdb062f16ee97ed8d2462dedb4565c860cd8ecc
    - http://example.3141-5926-5359.api.localhost:8000/
    - http://example.3141-5926-5359.api.localhost:8000/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126
    - http://example.3141-5926-5359.api.localhost:8000/config/
    - http://example.3141-5926-5359.api.localhost:8000/config/?session_key=9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126
    - http://localhost:8000/api/v1/chatbots/1/chat/
    - https://hr.smarter.querium.com/

    """

    def setUp(self):
        self.client = Client()
        self.wsgi_request_factory = RequestFactory()
        random_username = f"testuser_{uuid.uuid4().hex[:8]}"
        self.user = User.objects.create_user(username=random_username, password="12345")

    def tearDown(self):
        self.user.delete()

    def test_init_without_request_object(self):
        """
        Test that SmarterRequestMixin raises an error when instantiated without a request object.
        """
        with self.assertRaises(SmarterValueError):
            SmarterRequestMixin(request=None)

    def test_unauthenticated_instantiation(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        """

        self.client.login(username=self.user.username, password="12345")
        request = self.wsgi_request_factory.get("/")

        srm = SmarterRequestMixin(request)
        self.assertIsNotNone(srm.to_json())

    def test_authenticated_instantiation(self):
        """
        Test that SmarterRequestMixin can be instantiated with an authenticated request.
        """
        self.client.login(username=self.user.username, password="12345")
        response = self.client.get("/")
        request = response.wsgi_request

        srm = SmarterRequestMixin(request)
        self.assertIsNotNone(srm.to_json())

    def test_request_object_is_readonly(self):
        """
        Test that SmarterRequestMixin request object is read-only.
        """
        self.client.login(username=self.user.username, password="12345")
        response = self.client.get("/")
        request = response.wsgi_request

        srm = SmarterRequestMixin(request)
        with self.assertRaises(AttributeError):
            srm.request = None

    def test_unauthenticated_base_case(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        """
        request = self.wsgi_request_factory.get("/")
        srm = SmarterRequestMixin(request)
        self.assertIsNone(srm.account)
        self.assertIsNotNone(srm.session_key)
        self.assertEqual(srm.domain, "testserver")
        self.assertEqual(srm.ip_address, "127.0.0.1")
        self.assertIsNone(srm.chatbot_id)
        self.assertIsNone(srm.chatbot_name)
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
        self.assertIsNotNone(srm.session_key)
        self.assertIsInstance(srm.session_key, str)
        self.assertEqual(srm.domain, "example.3141-5926-5359.api.localhost:8000")

        self.assertEqual(srm.chatbot_name, "example")

    def test_sandbox_url(self):
        """
        Test that SmarterRequestMixin can be instantiated with an unauthenticated request.
        http://localhost:8000/chatbots/example/config/?session_key=1aeee4c1f183354247f43f80261573da921b0167c7c843b28afd3cb5ebba0d9a
        """
        url = "http://localhost:8000/chatbots/example/config/"
        smarter_admin_user_profile = get_cached_smarter_admin_user_profile()
        if smarter_admin_user_profile is None:
            self.skipTest("Smarter admin user profile is not available")

        self.client.login(username=smarter_admin_user_profile.user.username, password=SMARTER_DEV_ADMIN_PASSWORD)
        response = self.client.get(url, SERVER_NAME="localhost:8000")
        request = response.wsgi_request
        self.assertEqual(url, request.build_absolute_uri())
        if not request.user.is_authenticated:
            self.skipTest("User is not authenticated")

        srm = SmarterRequestMixin(request)

        # self.assertIsNone(srm.account)
        # self.assertEqual(srm.user, self.user)
        # self.assertEqual(srm.url, url)
        # self.assertTrue(srm.is_chatbot)
        # self.assertFalse(srm.is_chatbot_named_url)
        # self.assertFalse(srm.is_chatbot_cli_api_url)
        # self.assertTrue(srm.is_chatbot_sandbox_url)
        # self.assertFalse(srm.is_smarter_api)
        # self.assertIsNotNone(srm.session_key)
        # self.assertIsInstance(srm.session_key, str)
        # self.assertEqual(srm.domain, "localhost:8000")
        # self.assertEqual(srm.chatbot_name, "example")
