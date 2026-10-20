"""Test :mod:`smarter.apps.account.middleware`, which applies the profile that a user chose to each request."""

import asyncio

from django.contrib.sessions.backends.cache import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory

from smarter.apps.account.middleware import SmarterUserProfileSelectionMiddleware
from smarter.apps.account.profile_selection import (
    SELECTED_USER_PROFILE_SESSION_KEY,
    selected_user_profile_id,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSmarterUserProfileSelectionMiddleware(SmarterTestBase):
    """The session's choice is in selected_user_profile_id during the request, and only then."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.seen: list[int | None] = []

    def get_response(self, request):
        self.seen.append(selected_user_profile_id.get())
        return HttpResponse("ok")

    async def aget_response(self, request):
        self.seen.append(selected_user_profile_id.get())
        return HttpResponse("ok")

    def request(self, value=None, path: str = "/dashboard/", **headers):
        request = self.factory.get(path, headers=headers)
        request.session = SessionStore()
        if value is not None:
            request.session[SELECTED_USER_PROFILE_SESSION_KEY] = value
        return request

    def call(self, request):
        middleware = SmarterUserProfileSelectionMiddleware(self.get_response)
        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        return self.seen[-1]

    def test_sets_the_choice_for_the_request_and_resets_it(self):
        self.assertEqual(self.call(self.request(12)), 12)
        self.assertIsNone(selected_user_profile_id.get())

    def test_no_choice(self):
        self.assertIsNone(self.call(self.request()))

    def test_no_session(self):
        request = self.factory.get("/dashboard/")
        self.assertIsNone(self.call(request))

    def test_a_malformed_choice_is_ignored(self):
        self.assertEqual(self.call(self.request("12")), 12)
        self.assertIsNone(self.call(self.request("twelve")))
        self.assertIsNone(self.call(self.request(["12"])))

    def test_api_key_requests_ignore_the_session(self):
        self.assertIsNone(self.call(self.request(12, Authorization="Token abc")))
        self.assertEqual(self.call(self.request(12, Authorization="Bearer abc")), 12)

    def test_amnesty_paths_are_skipped(self):
        middleware = SmarterUserProfileSelectionMiddleware(self.get_response)
        path = next(iter(middleware.amnesty_urls))
        self.assertIsNone(self.call(self.request(12, path=f"/{path}")))

    def test_async(self):
        middleware = SmarterUserProfileSelectionMiddleware(self.aget_response)
        self.assertTrue(middleware.async_mode)
        for request, expected in (
            (self.request(12), 12),
            (self.request(), None),
            (self.request(12, Authorization="Token abc"), None),
            (self.factory.get("/dashboard/"), None),
        ):
            with self.subTest(expected=expected):
                response = asyncio.run(middleware(request))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.seen[-1], expected)
        self.assertIsNone(selected_user_profile_id.get())

    def test_formatted_class_name(self):
        middleware = SmarterUserProfileSelectionMiddleware(self.get_response)
        self.assertIn("SmarterUserProfileSelectionMiddleware", middleware.formatted_class_name)
