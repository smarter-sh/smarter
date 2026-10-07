"""Test :class:`smarter.lib.django.middleware.debug.MiddlewareDebugMiddleware`."""

import asyncio

from django.http import HttpResponse
from django.test import RequestFactory

from smarter.lib.django.middleware.debug import MiddlewareDebugMiddleware
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestMiddlewareDebugMiddleware(SmarterTestBase):
    """Test that the middleware passes responses through, and refuses anything that isn't a response."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_sync(self):
        middleware = MiddlewareDebugMiddleware(lambda request: HttpResponse("ok"))
        self.assertEqual(middleware(self.factory.get("/a/")).content, b"ok")
        self.assertEqual(middleware(self.factory.get("/healthz/")).content, b"ok")
        self.assertIn("MiddlewareDebugMiddleware", middleware.formatted_class_name)

    def test_sync_amnesty_skips_the_type_check(self):
        middleware = MiddlewareDebugMiddleware(lambda request: "not a response")
        self.assertEqual(middleware(self.factory.get("/healthz/")), "not a response")

    def test_sync_invalid_response(self):
        """Test that the mixin's assertion refuses a get_response that doesn't return a response."""
        middleware = MiddlewareDebugMiddleware(lambda request: "not a response")
        with self.assertRaises((AssertionError, TypeError)):
            middleware(self.factory.get("/a/"))

    def test_async(self):
        calls = []

        async def get_response(request):
            calls.append(request.path)
            return HttpResponse("async ok")

        middleware = MiddlewareDebugMiddleware(get_response)
        self.assertEqual(asyncio.run(middleware(self.factory.get("/a/"))).content, b"async ok")
        self.assertEqual(len(calls), 1)
