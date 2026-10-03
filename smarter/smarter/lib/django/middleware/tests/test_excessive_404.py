"""Test :class:`smarter.lib.django.middleware.excessive_404.SmarterBlockExcessive404Middleware`."""

import asyncio
import unittest
from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpResponseNotFound
from django.test import RequestFactory

from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django.middleware.excessive_404 import (
    SmarterBlockExcessive404Middleware,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.lib.django.middleware.excessive_404"


class TestSmarterBlockExcessive404Middleware(SmarterTestBase):
    """Test that 404s are counted for each anonymous client ip."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        patcher = patch("smarter.lib.django.waffle.switch_is_active", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ip = "8.8.7.7"
        self.key = SmarterBlockExcessive404Middleware.get_throttle_key(self.ip)
        cache.delete(self.key)
        self.addCleanup(cache.delete, self.key)

    def request(self, path="/not-found/", ip=None):
        request = self.factory.get(path, REMOTE_ADDR=ip or self.ip)
        request.user = AnonymousUser()
        return request

    def test_404_is_counted(self):
        middleware = SmarterBlockExcessive404Middleware(lambda request: HttpResponseNotFound())
        for count in range(1, 4):
            self.assertEqual(middleware(self.request()).status_code, HTTPStatus.NOT_FOUND)
            self.assertEqual(cache.get(self.key), count)

    def test_not_counted(self):
        """Test that a 200, an amnesty path, a private ip, an authenticated user and the switch off aren't counted."""
        ok = SmarterBlockExcessive404Middleware(lambda request: HttpResponse("ok"))
        not_found = SmarterBlockExcessive404Middleware(lambda request: HttpResponseNotFound())
        ok(self.request())
        not_found(self.request("/healthz/"))
        not_found(self.request(ip="10.0.0.1"))
        with patch(f"{MODULE}.is_authenticated_request", return_value=True):
            not_found(self.request())
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            not_found(self.request())
        self.assertIsNone(cache.get(self.key))

    def test_throttled_client_gets_403(self):
        """Test that _process_response() refuses a client that has exceeded the limit."""
        middleware = SmarterBlockExcessive404Middleware(lambda request: HttpResponseNotFound())
        cache.set(self.key, SmarterBlockExcessive404Middleware.THROTTLE_LIMIT, timeout=60)
        response = middleware._process_response(
            self.request(), HttpResponseNotFound()
        )  # pylint: disable=protected-access
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_throttled_client_is_blocked(self):
        """Test that the middleware blocks a client that has exceeded the limit, sync and async."""
        middleware = SmarterBlockExcessive404Middleware(lambda request: HttpResponseNotFound())
        cache.set(self.key, SmarterBlockExcessive404Middleware.THROTTLE_LIMIT, timeout=60)
        self.assertEqual(middleware(self.request()).status_code, HTTPStatus.FORBIDDEN)

        async def get_response(request):
            return HttpResponseNotFound()

        middleware = SmarterBlockExcessive404Middleware(get_response)
        with patch("smarter.lib.django.waffle.async_switch_is_active", return_value=True):
            self.assertEqual(asyncio.run(middleware(self.request())).status_code, HTTPStatus.FORBIDDEN)
        with patch("smarter.lib.django.waffle.async_switch_is_active", return_value=False):
            self.assertEqual(asyncio.run(middleware(self.request())).status_code, HTTPStatus.NOT_FOUND)

    def test_log_sampling(self):
        middleware = SmarterBlockExcessive404Middleware(lambda request: HttpResponseNotFound())
        with patch(f"{MODULE}.logger") as logger:
            middleware.log_404_event(self.request(), self.ip, blocked_count=1)
            logger.debug.assert_not_called()
            middleware.log_404_event(self.request(), self.ip, blocked_count=middleware.LOG_SAMPLE_RATE)
            logger.debug.assert_called_once()

    def test_async(self):
        async def get_response(request):
            return HttpResponseNotFound()

        middleware = SmarterBlockExcessive404Middleware(get_response)
        with patch("smarter.lib.django.waffle.async_switch_is_active", return_value=True):
            self.assertEqual(asyncio.run(middleware(self.request())).status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(cache.get(self.key), 1)
