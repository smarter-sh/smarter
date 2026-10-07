"""Test the auth token list view's react-integration api, :mod:`smarter.lib.drf.views.listview.api`."""

import uuid
from http import HTTPStatus

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib import json
from smarter.lib.drf.const import namespace
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.urls import AuthTokenReverseNames
from smarter.lib.drf.views.listview.api import (
    AuthTokenListApiCloneView,
    AuthTokenListApiDeleteView,
    AuthTokenListApiRenameView,
)


class TestAuthTokenListApi(TestAccountMixin):
    """Test listing, cloning, renaming and deleting auth tokens with the react-integration api."""

    def setUp(self):
        super().setUp()
        self.token, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile, name="test_listview_api_token", user=self.admin_user, description="test"
        )
        self.addCleanup(
            SmarterAuthToken.objects.filter(user_profile=self.user_profile, name__startswith="test_listview_api").delete
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)
        self.factory = RequestFactory()
        self.token_id = self.token.key_id

    def call(self, view_class, **kwargs):
        """Call a view directly, as the admin user, with the kwargs that the view reads."""
        request = self.factory.post("/", HTTP_HOST="localhost:9357")
        SessionMiddleware(lambda r: None).process_request(request)  # type: ignore[arg-type]
        request.user = self.admin_user
        response = view_class.as_view()(request, **kwargs)
        return response, json.loads(response.content)

    def test_list(self):
        """Test that the list includes the user's token, for each ownership filter."""
        for name, kwargs in (
            (AuthTokenReverseNames.listview_api_all, {}),
            (AuthTokenReverseNames.listview_api, {"ownership_filter": "owned"}),
            (AuthTokenReverseNames.listview_api, {"ownership_filter": "shared"}),
            (AuthTokenReverseNames.listview_api, {"ownership_filter": "all"}),
        ):
            with self.subTest(kwargs=kwargs):
                url = reverse(f"{namespace}:{name}", kwargs=kwargs)
                response = self.client.post(f"{url}?invalidate_cache=true&page_size=100")
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
                data = response.json()
                self.assertEqual(set(data.keys()), {"user", "admin", "objects"})
                if kwargs.get("ownership_filter") != "shared":
                    self.assertIn(self.token.name, [obj["name"] for obj in data["objects"]])

    def test_clone(self):
        response, data = self.call(
            AuthTokenListApiCloneView, authtoken_id=self.token_id, new_name="test_listview_api_clone"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, data)
        self.assertEqual(data["name"], "test_listview_api_clone")
        self.assertTrue(
            SmarterAuthToken.objects.filter(user_profile=self.user_profile, name="test_listview_api_clone").exists()
        )

    def test_rename(self):
        response, data = self.call(
            AuthTokenListApiRenameView, authtoken_id=self.token_id, new_name="test_listview_api_renamed"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, data)
        self.token.refresh_from_db()
        self.assertEqual(self.token.name, "test_listview_api_renamed")

    def test_delete(self):
        response, data = self.call(AuthTokenListApiDeleteView, authtoken_id=self.token_id)
        self.assertEqual(response.status_code, HTTPStatus.OK, data)
        self.assertFalse(SmarterAuthToken.objects.filter(key_id=self.token_id).exists())

    def test_missing_arguments(self):
        """Test that a missing id or name is a 400."""
        for view_class, kwargs, status in (
            (AuthTokenListApiCloneView, {}, HTTPStatus.BAD_REQUEST),
            (AuthTokenListApiRenameView, {"authtoken_id": self.token_id}, HTTPStatus.BAD_REQUEST),
            (AuthTokenListApiDeleteView, {}, HTTPStatus.BAD_REQUEST),
        ):
            with self.subTest(view=view_class.__name__, kwargs=kwargs):
                response, _ = self.call(view_class, **kwargs)
                self.assertEqual(response.status_code, status)

    def test_urls(self):
        """Test cloning and renaming a token by its urls, which identify it by its key_id."""
        url = reverse(
            f"{namespace}:{AuthTokenReverseNames.listview_api_clone}",
            args=[self.token_id, "test_listview_api_url_clone"],
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertEqual(response.json()["name"], "test_listview_api_url_clone")
        url = reverse(
            f"{namespace}:{AuthTokenReverseNames.listview_api_rename}",
            args=[self.token_id, "test_listview_api_url_renamed"],
        )
        self.assertEqual(self.client.post(url).status_code, HTTPStatus.OK)
        self.token.refresh_from_db()
        self.assertEqual(self.token.name, "test_listview_api_url_renamed")

    def test_not_found(self):
        for view_class, kwargs in (
            (AuthTokenListApiCloneView, {"authtoken_id": uuid.uuid4(), "new_name": "x"}),
            (AuthTokenListApiRenameView, {"authtoken_id": uuid.uuid4(), "new_name": "x"}),
            (AuthTokenListApiDeleteView, {"authtoken_id": uuid.uuid4()}),
        ):
            with self.subTest(view=view_class.__name__):
                response, _ = self.call(view_class, **kwargs)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_delete_url(self):
        """Test deleting a token by its url."""
        url = reverse(f"{namespace}:{AuthTokenReverseNames.listview_api_delete}", args=[self.token_id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
