"""
Test the social auth pipeline and middleware, :mod:`smarter.apps.account.pipeline`.

The profile image is never fetched: requests.head is mocked.
"""

import asyncio
import unittest
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from social_core.exceptions import AuthAlreadyAssociated

from smarter.apps.account import pipeline
from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin

MODULE = "smarter.apps.account.pipeline"
IMAGE = "https://example.com/picture.png"


class TestPipeline(TestAccountMixin):
    """Test create_user(), user_details() and redirect_inactive_account()."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_create_user_existing(self):
        self.assertEqual(
            pipeline.create_user(None, {}, None, user=self.admin_user), {"is_new": False, "user": self.admin_user}
        )

    def test_create_user_new(self):
        """Test that a new user is inactive, with a profile in the Smarter account."""
        username = "test_pipeline_new_user"
        self.addCleanup(User.objects.filter(username=username).delete)
        strategy = MagicMock()
        strategy.create_user.side_effect = lambda **fields: User.objects.create(**fields)
        details = {"username": username, "email": "new@example.com", "first_name": "New", "last_name": "User"}
        result = pipeline.create_user(strategy, details, None)
        self.assertTrue(result["is_new"])
        self.assertFalse(result["user"].is_active)
        self.assertTrue(UserProfile.objects.filter(user=result["user"]).exists())

    def test_create_user_without_names(self):
        """Test that a user is created when the provider doesn't send their names, as GitHub often doesn't."""
        username = "test_pipeline_unnamed_user"
        self.addCleanup(User.objects.filter(username=username).delete)
        strategy = MagicMock()
        strategy.create_user.side_effect = lambda **fields: User.objects.create(**fields)
        result = pipeline.create_user(strategy, {"username": username, "email": "unnamed@example.com"}, None)
        self.assertTrue(result["is_new"])
        self.assertEqual(result["user"].first_name, "")

    def test_create_user_without_username(self):
        self.assertEqual(
            pipeline.create_user(MagicMock(), {"email": "x@example.com"}, None), {"is_new": False, "user": None}
        )

    def test_user_details(self):
        """Test that the user's names and email are updated, and the profile image is stored."""
        self.addCleanup(
            User.objects.filter(pk=self.non_admin_user.pk).update,
            first_name=self.non_admin_user.first_name,
            last_name=self.non_admin_user.last_name,
            email=self.non_admin_user.email,
        )
        self.assertIsNone(pipeline.user_details(None, {}, None))
        details = {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com"}
        with patch(f"{MODULE}.requests.head", return_value=MagicMock(status_code=HTTPStatus.OK)) as head:
            pipeline.user_details(None, details, None, user=self.non_admin_user, response={"picture": IMAGE})
        head.assert_called_once_with(IMAGE, timeout=1)
        user = User.objects.get(pk=self.non_admin_user.pk)
        self.assertEqual((user.first_name, user.last_name, user.email), ("Ada", "Lovelace", "ada@example.com"))
        self.assertEqual(UserProfile.objects.get(pk=self.non_admin_user_profile.pk).profile_image_url, IMAGE)

    def test_user_details_without_image(self):
        """Test that an unchanged user, a missing image and an image that can't be fetched change nothing."""
        user = self.non_admin_user
        details = {"first_name": user.first_name, "last_name": user.last_name, "email": user.email}
        self.assertIsNone(pipeline.user_details(None, details, None, user=user))
        with patch(f"{MODULE}.requests.head", return_value=MagicMock(status_code=HTTPStatus.NOT_FOUND)):
            self.assertIsNone(pipeline.user_details(None, details, None, user=user, response={"picture": IMAGE}))
        with patch(f"{MODULE}.requests.head", side_effect=requests.RequestException("down")):
            self.assertIsNone(pipeline.user_details(None, details, None, user=user, response={"picture": IMAGE}))

    def test_redirect_inactive_account(self):
        request = self.factory.get("/")
        SessionMiddleware(lambda r: None).process_request(request)  # type: ignore[arg-type]
        strategy = MagicMock(request=request)
        self.assertIsNone(pipeline.redirect_inactive_account(strategy, {}, user=self.admin_user))
        request.session["account_status"] = "inactive"
        response = pipeline.redirect_inactive_account(strategy, {}, user=self.admin_user)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertNotIn("account_status", request.session)
        inactive = MagicMock(is_active=False)
        self.assertEqual(pipeline.redirect_inactive_account(strategy, {}, user=inactive).status_code, HTTPStatus.FOUND)


class TestSmarterSocialAuthExceptionMiddleware(TestAccountMixin):
    """Test that an already associated social account is redirected, and the middleware passes requests through."""

    def test_call(self):
        middleware = pipeline.SmarterSocialAuthExceptionMiddleware(lambda request: HttpResponse("ok"))
        self.assertEqual(middleware(RequestFactory().get("/")).content, b"ok")

    def test_async_call(self):
        async def get_response(request):
            return HttpResponse("async ok")

        middleware = pipeline.SmarterSocialAuthExceptionMiddleware(get_response)
        self.assertEqual(asyncio.run(middleware(RequestFactory().get("/"))).content, b"async ok")

    def test_process_exception(self):
        middleware = pipeline.SmarterSocialAuthExceptionMiddleware(lambda request: HttpResponse("ok"))
        request = RequestFactory().get("/")
        response = middleware.process_exception(request, AuthAlreadyAssociated(MagicMock()))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        with patch(
            "social_django.middleware.SocialAuthExceptionMiddleware.process_exception", return_value=None
        ) as parent:
            self.assertIsNone(middleware.process_exception(request, ValueError("other")))
        parent.assert_called_once()
