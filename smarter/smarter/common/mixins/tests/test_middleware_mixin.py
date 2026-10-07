"""Test :class:`smarter.common.mixins.middleware_mixin.SmarterMiddlewareMixin`."""

import asyncio
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse

from smarter.common.mixins.middleware_mixin import SmarterMiddlewareMixin
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.common.mixins.middleware_mixin"


def make_request(path: str = "/api/v1/", **meta) -> HttpRequest:
    request = HttpRequest()
    request.path = path
    request.META.update(meta)
    request.user = AnonymousUser()
    return request


class TestSmarterMiddlewareMixin(SmarterTestBase):
    """Test the middleware mixin's sync and async calls, client ip and authentication indicators."""

    def setUp(self):
        super().setUp()
        self.middleware = SmarterMiddlewareMixin(lambda request: HttpResponse("ok"))

    def test_sync_call(self):
        """Test that a sync middleware returns the response, and sets the request's process id."""
        request = make_request()
        response = self.middleware(request)
        self.assertEqual(response.content, b"ok")
        self.assertFalse(self.middleware.async_mode)
        self.assertEqual(request.smarter_process_id, self.middleware.smarter_process_id)

    def test_process_id_is_not_overwritten(self):
        """Test that the first middleware's process id is kept by the next middlewares."""
        request = make_request()
        request.smarter_process_id = 42
        self.middleware(request)
        self.assertEqual(request.smarter_process_id, 42)

    def test_async_call(self):
        async def get_response(request):
            return HttpResponse("async ok")

        middleware = SmarterMiddlewareMixin(get_response)
        self.assertTrue(middleware.async_mode)
        request = make_request()
        response = asyncio.run(middleware(request))
        self.assertEqual(response.content, b"async ok")
        self.assertEqual(request.smarter_process_id, middleware.smarter_process_id)

    def test_client_ip_headers(self):
        """Test that the first public ip of X-Forwarded-For, X-Real-IP, CF-Connecting-IP and REMOTE_ADDR is used."""
        cases = [
            ({"HTTP_X_FORWARDED_FOR": "8.8.8.8, 10.0.0.1", "REMOTE_ADDR": "10.0.0.2"}, "8.8.8.8"),
            ({"HTTP_X_FORWARDED_FOR": "10.0.0.1", "HTTP_X_REAL_IP": " 1.1.1.1 "}, "1.1.1.1"),
            ({"HTTP_X_REAL_IP": "192.168.1.1", "HTTP_CF_CONNECTING_IP": "9.9.9.9"}, "9.9.9.9"),
            ({"REMOTE_ADDR": "4.4.4.4"}, "4.4.4.4"),
        ]
        for meta, expected in cases:
            with self.subTest(meta=meta):
                self.assertEqual(self.middleware.get_client_ip(make_request(**meta)), expected)

    def test_client_ip_private(self):
        """Test that a request from only private ips has no client ip, and is logged unless it deserves amnesty."""
        settings = MagicMock(environment_is_local=False)
        with patch(f"{MODULE}.smarter_settings", settings), patch(f"{MODULE}.logger") as logger:
            self.assertIsNone(
                self.middleware.get_client_ip(make_request(REMOTE_ADDR="10.0.0.1", HTTP_HOST="testserver"))
            )
            logger.warning.assert_called_once()
            logger.reset_mock()
            self.assertIsNone(self.middleware.get_client_ip(make_request("/healthz/", REMOTE_ADDR="127.0.0.1")))
            logger.warning.assert_not_called()

    def test_is_private_ip(self):
        for ip, private in (
            ("10.0.0.1", True),
            ("127.0.0.1", True),
            ("169.254.1.1", True),
            ("8.8.8.8", False),
            ("not an ip", True),
            (MagicMock(), True),
        ):
            with self.subTest(ip=ip):
                self.assertEqual(self.middleware._is_private_ip(ip), private)  # pylint: disable=protected-access

    def test_has_auth_indicators(self):
        cases = [
            ({"sessionid": "abc"}, {}),
            ({"csrftoken": "abc"}, {}),
            ({}, {"HTTP_AUTHORIZATION": "Token abc"}),
            ({}, {"HTTP_X_API_KEY": "abc"}),
        ]
        for cookies, meta in cases:
            request = make_request(**meta)
            request.COOKIES.update(cookies)
            with self.subTest(cookies=cookies, meta=meta):
                self.assertTrue(self.middleware.has_auth_indicators(request))
        self.assertFalse(self.middleware.has_auth_indicators(make_request()))
        with patch(f"{MODULE}.is_authenticated_request", return_value=True):
            self.assertTrue(self.middleware.has_auth_indicators(make_request()))
