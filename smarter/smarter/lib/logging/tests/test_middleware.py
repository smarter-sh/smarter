"""Test :class:`smarter.lib.logging.middleware.SmarterRequestLogContextMiddleware`."""

import asyncio
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.logging.middleware import SmarterRequestLogContextMiddleware
from smarter.lib.logging.redis_log_handler import get_user_context, user_id_context


class TestSmarterRequestLogContextMiddleware(TestAccountMixin):
    """Test that the logging context is the user's while the view runs, and is reset afterwards."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.seen = []
        patcher = patch("smarter.lib.django.waffle.switch_is_active", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def get_response(self, request):
        self.seen.append(user_id_context.get())
        return HttpResponse("ok")

    def request(self, path="/dashboard/", user=None):
        request = self.factory.get(path)
        request.user = user or AnonymousUser()
        return request

    def test_authenticated_user(self):
        middleware = SmarterRequestLogContextMiddleware(self.get_response)
        before = user_id_context.get()
        self.assertEqual(middleware(self.request(user=self.admin_user)).content, b"ok")
        self.assertEqual(self.seen, [get_user_context(self.admin_user)])
        self.assertEqual(user_id_context.get(), before)

    def test_anonymous_user_gets_a_job_id(self):
        SmarterRequestLogContextMiddleware(self.get_response)(self.request())
        self.assertTrue(self.seen[0])
        self.assertNotEqual(self.seen[0], get_user_context(self.admin_user))

    def test_switch_off_and_amnesty(self):
        middleware = SmarterRequestLogContextMiddleware(self.get_response)
        middleware(self.request("/healthz/", user=self.admin_user))
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            middleware(self.request(user=self.admin_user))
        self.assertEqual(self.seen, [None, None])

    def test_async(self):
        seen = []

        async def get_response(request):
            seen.append(user_id_context.get())
            return HttpResponse("async ok")

        middleware = SmarterRequestLogContextMiddleware(get_response)
        admin_user = self.admin_user

        async def auser():
            return admin_user

        request = self.request()
        request.auser = auser
        with patch("smarter.lib.django.waffle.async_switch_is_active", return_value=True):
            self.assertEqual(asyncio.run(middleware(request)).content, b"async ok")
            asyncio.run(middleware(self.request()))  # no auser
        with patch("smarter.lib.django.waffle.async_switch_is_active", return_value=False):
            asyncio.run(middleware(request))
        self.assertEqual(seen[0], get_user_context(admin_user))
        self.assertTrue(seen[1])
        self.assertEqual(len(seen), 3)

    def test_async_anonymous_auser(self):
        async def auser():
            return AnonymousUser()

        middleware = SmarterRequestLogContextMiddleware(self.get_response)
        request = self.request()
        request.auser = auser
        context = asyncio.run(middleware.get_async_context(request))
        self.assertNotEqual(context, get_user_context(self.admin_user))

    def test_is_authenticated(self):
        self.assertFalse(SmarterRequestLogContextMiddleware.is_authenticated(None))
        self.assertFalse(SmarterRequestLogContextMiddleware.is_authenticated(AnonymousUser()))
        self.assertTrue(SmarterRequestLogContextMiddleware.is_authenticated(self.admin_user))
