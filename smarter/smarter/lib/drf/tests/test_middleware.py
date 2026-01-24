"""Test SmarterTokenAuthenticationMiddleware."""

from datetime import timedelta
from http import HTTPStatus
from logging import getLogger

from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from rest_framework.authentication import get_authorization_header
from rest_framework.test import APIClient

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.api.v1.tests.urls import ApiV1TestUrls
from smarter.lib.drf.middleware import SmarterTokenAuthenticationMiddleware

logger = getLogger(__name__)


class TestSmarterTokenAuthenticationMiddleware(ApiV1TestBase):
    """
    Test SmarterTokenAuthenticationMiddleware.
    """

    def setUp(self):
        super().setUp()
        self.middleware = SmarterTokenAuthenticationMiddleware(lambda req: req)
        self.client = APIClient()
        self.path = reverse(f"{ApiV1TestUrls.namespace}{ApiV1TestUrls.AUTHENTICATED_DICT}")

    def test_non_api_endpoint_skips_auth(self):
        # Should skip authentication for non-API endpoint
        request = HttpRequest()
        request.path = "/not-api/"
        request.method = "POST"
        response = self.middleware(request)
        self.assertEqual(response, request)

    def test_no_authorization_header(self):
        # Should skip if no Authorization header
        request = HttpRequest()
        request.method = "POST"
        response = self.middleware(request)
        self.assertEqual(response, request)

    def test_invalid_authorization_prefix(self):
        # Should skip if Authorization header is not Token
        request = HttpRequest()
        request.method = "POST"
        request.META = {"HTTP_AUTHORIZATION": "Bearer something"}
        self.middleware.authorization_header = get_authorization_header(request).decode()
        response = self.middleware(request)
        self.assertEqual(response, request)

    def test_valid_token_authenticates(self):
        # Should authenticate with valid token
        response_json, status = self.get_response(self.path)
        self.assertIsInstance(response_json, dict)
        self.assertEqual(status, HTTPStatus.OK)

    def test_expired_token_warning(self):
        # Should return a 40X response if token is expired
        self.token_record.expiry = timezone.now() - timedelta(days=1)
        self.token_record.save()

        response_json, status = self.get_response(self.path)
        self.assertIsInstance(response_json, dict)
        self.assertEqual(status, HTTPStatus.UNAUTHORIZED)

    def test_authentication_failed(self):
        # Should return error for invalid token
        client = APIClient()
        headers = {"Authorization": "Token invalidtoken1234567890"}
        logger.warning("*" * 80)
        response = client.post(path=self.path, content_type="application/json", headers=headers)
        logger.warning("*" * 80)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        try:
            response_json = response.json()
            self.assertIn("error", response_json)
        # pylint: disable=broad-except
        except Exception:
            pass

    def test_already_authenticated(self):
        # Should skip if request.auth is already set
        request = HttpRequest()
        request.method = "POST"
        request.auth = "already_authenticated"
        response = self.middleware(request)
        self.assertEqual(response, request)

    def test_url_method(self):
        # Should return full URL
        request = HttpRequest()
        self.middleware.request = request
        url = self.middleware.url()
        self.assertIsInstance(url, str)

    def test_is_token_auth_true(self):
        # Should return True for valid Token header
        request = HttpRequest()
        request.META = {"HTTP_AUTHORIZATION": f"Token {self.token_key}"}
        self.middleware.authorization_header = get_authorization_header(request).decode()
        result = self.middleware.is_token_auth(request)
        self.assertTrue(result)

    def test_is_token_auth_false(self):
        # Should return False for missing/invalid header
        request = HttpRequest()
        request.META = {"HTTP_AUTHORIZATION": "Bearer something"}
        self.middleware.authorization_header = get_authorization_header(request).decode()
        result = self.middleware.is_token_auth(request)
        self.assertFalse(result)
