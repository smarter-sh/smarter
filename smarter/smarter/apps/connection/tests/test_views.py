"""
Test the connection app's views: :mod:`smarter.apps.connection.views.listview`, the React connection list and its api, and :mod:`smarter.apps.connection.views.detailview`.

The class fixture ``connection_django_model`` is owned by the account's admin user.
"""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.connection.caching import (
    invalidate_all_cached_connections_for_user_profile,
)
from smarter.apps.connection.models import ApiConnection, SqlConnection
from smarter.apps.connection.urls import ConnectionReverseNames
from smarter.lib import json

from .mixins import ApiConnectionTestMixin, SqlConnectionTestMixin

NAMESPACE = ConnectionReverseNames.namespace


class ViewTestMixin:
    """Helpers for posting to the connection app's views as a logged in user."""

    def setUp(self):
        super().setUp()  # type: ignore[misc]
        self.client = Client()
        self.addCleanup(self.client.logout)  # type: ignore[attr-defined]
        self.client.force_login(self.admin_user)  # type: ignore[attr-defined]
        invalidate_all_cached_connections_for_user_profile(self.user_profile)  # type: ignore[attr-defined]
        invalidate_all_cached_connections_for_user_profile(self.non_admin_user_profile)  # type: ignore[attr-defined]

    def url(self, name: str, **kwargs) -> str:
        return reverse(f"{NAMESPACE}:{name}", kwargs=kwargs or None)

    def post(self, url: str, status: int = HTTPStatus.OK) -> dict:
        """POST to ``url``, assert the response's status, and return its json."""
        response = self.client.post(url)
        self.assertEqual(response.status_code, status, response.content[:500])  # type: ignore[attr-defined]
        return json.loads(response.content)


class TestConnectionListViews(ViewTestMixin, ApiConnectionTestMixin):
    """Test the React connection list page and its list, clone, delete and rename api views."""

    def listed(self, ownership_filter=None, **params) -> list[str]:
        """Return the names of the connections that the list api returns."""
        if ownership_filter:
            url = self.url(ConnectionReverseNames.listview_api, ownership_filter=ownership_filter)
        else:
            url = self.url(ConnectionReverseNames.listview_api_all)
        if params:
            url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
        data = self.post(url)
        return [connection["name"] for connection in data["objects"]]

    def new_connection(self, name: str) -> ApiConnection:
        """Return a copy of the class fixture named ``name``, which is deleted after the test."""
        connection = self.connection_django_model.clone(new_name=name)  # type: ignore[union-attr]
        self.addCleanup(ApiConnection.objects.filter(name=name, user_profile=self.user_profile).delete)
        return ApiConnection.objects.get(pk=connection.pk)

    # -------------------------------------------------------------------------
    # ConnectionListView
    # -------------------------------------------------------------------------
    def test_list_page(self):
        """Test that the list page renders the React app's root and its api url."""
        response = self.client.get(self.url(ConnectionReverseNames.listview))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn(b"smarter-connection-list-root", response.content)

    # -------------------------------------------------------------------------
    # ConnectionListApiView
    # -------------------------------------------------------------------------
    def test_list(self):
        """Test that the list api returns the user, the smarter admin user, and the connections."""
        data = self.post(self.url(ConnectionReverseNames.listview_api_all))
        self.assertIn("user", data)
        self.assertIn("admin", data)
        self.assertIn(self.connection_django_model.name, [c["name"] for c in data["objects"]])  # type: ignore[union-attr]

    def test_list_get(self):
        """Test that a GET is answered as a POST."""
        response = self.client.get(self.url(ConnectionReverseNames.listview_api_all))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_list_filters(self):
        """Test the owned, shared and all filters, for the owner and for another user of the account."""
        name = self.connection_django_model.name  # type: ignore[union-attr]
        self.assertIn(name, self.listed("owned"))
        self.assertNotIn(name, self.listed("shared"))
        self.assertIn(name, self.listed("all"))
        self.client.force_login(self.non_admin_user)
        self.assertNotIn(name, self.listed("owned"))

    def test_list_pagination_and_invalidate_cache(self):
        """Test that the list api paginates, most recently updated first, and that invalidate_cache shows a new connection."""
        name = "test_connection_views_newest"
        self.listed("owned")
        self.new_connection(name)
        self.assertEqual(self.listed("owned", page_size=1, invalidate_cache="true"), [name])
        self.assertIn(self.connection_django_model.name, self.listed("owned", page_size=1, page=2))  # type: ignore[union-attr]

    def test_list_anonymous_user(self):
        """Test that an anonymous user is redirected to the login page."""
        self.client.logout()
        response = self.client.post(self.url(ConnectionReverseNames.listview_api_all))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    # -------------------------------------------------------------------------
    # ConnectionListApiCloneView, ConnectionListApiDeleteView, ConnectionListApiRenameView
    # -------------------------------------------------------------------------
    def test_clone(self):
        """Test that the clone api creates an ApiConnection named new_name, and returns it."""
        clone_name = "test_connection_views_clone"
        self.addCleanup(ApiConnection.objects.filter(name=clone_name).delete)
        url = self.url(
            ConnectionReverseNames.listview_api_clone,
            connection_id=self.connection_django_model.id,  # type: ignore[union-attr]
            new_name=clone_name,
        )
        data = self.post(url)
        self.assertEqual(data["name"], clone_name)
        self.assertTrue(ApiConnection.objects.filter(name=clone_name, user_profile=self.user_profile).exists())

    def test_delete(self):
        """Test that the delete api deletes the connection."""
        connection = self.new_connection("test_connection_views_delete")
        self.post(self.url(ConnectionReverseNames.listview_api_delete, connection_id=connection.id))
        self.assertFalse(ApiConnection.objects.filter(pk=connection.pk).exists())

    def test_rename(self):
        """Test that the rename api renames the connection."""
        connection = self.new_connection("test_connection_views_rename")
        new_name = "test_connection_views_renamed"
        self.addCleanup(ApiConnection.objects.filter(name=new_name).delete)
        data = self.post(
            self.url(ConnectionReverseNames.listview_api_rename, connection_id=connection.id, new_name=new_name)
        )
        self.assertEqual(data["name"], new_name)
        self.assertEqual(ApiConnection.objects.get(pk=connection.pk).name, new_name)

    def test_clone_delete_rename_unknown_connection(self):
        """Test that the clone, delete and rename apis answer an unknown connection_id with a 404."""
        connection_id = 999999999
        for url in (
            self.url(ConnectionReverseNames.listview_api_clone, connection_id=connection_id, new_name="x"),
            self.url(ConnectionReverseNames.listview_api_delete, connection_id=connection_id),
            self.url(ConnectionReverseNames.listview_api_rename, connection_id=connection_id, new_name="x"),
        ):
            with self.subTest(url=url):
                data = self.post(url, status=HTTPStatus.NOT_FOUND)
                self.assertIn("error", data)


class TestApiConnectionDetailView(ViewTestMixin, ApiConnectionTestMixin):
    """Test :class:`smarter.apps.connection.views.detailview.ApiConnectionDetailView`."""

    def detail_url(self, hashed_id: str) -> str:
        return self.url(ConnectionReverseNames.api_detailview, hashed_id=hashed_id)

    def test_detail(self):
        """Test that the detail view renders the connection's manifest, which has a proxy password."""
        response = self.client.get(self.detail_url(self.connection_django_model.hashed_id))  # type: ignore[union-attr]
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertIn(self.connection_django_model.name.encode(), response.content)  # type: ignore[union-attr]

    def test_detail_not_found(self):
        """Test that an invalid, or unknown, hashed id is a 404."""
        self.assertEqual(self.client.get(self.detail_url("not-a-hashed-id")).status_code, HTTPStatus.NOT_FOUND)
        unknown = ApiConnection(id=999999999)
        self.assertEqual(self.client.get(self.detail_url(unknown.hashed_id)).status_code, HTTPStatus.NOT_FOUND)


class TestSqlConnectionDetailView(ViewTestMixin, SqlConnectionTestMixin):
    """Test :class:`smarter.apps.connection.views.detailview.SqlConnectionDetailView`."""

    def detail_url(self, hashed_id: str) -> str:
        return self.url(ConnectionReverseNames.sql_detailview, hashed_id=hashed_id)

    def test_detail(self):
        """Test that the detail view renders the connection's manifest."""
        response = self.client.get(self.detail_url(self.connection_django_model.hashed_id))  # type: ignore[union-attr]
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertIn(self.connection_django_model.name.encode(), response.content)  # type: ignore[union-attr]

    def test_detail_non_admin_user(self):
        """Test that another user of the account sees the connection that the account's admin owns."""
        self.client.force_login(self.non_admin_user)
        response = self.client.get(self.detail_url(self.connection_django_model.hashed_id))  # type: ignore[union-attr]
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])

    def test_detail_not_found(self):
        """Test that an invalid, or unknown, hashed id is a 404."""
        self.assertEqual(self.client.get(self.detail_url("not-a-hashed-id")).status_code, HTTPStatus.NOT_FOUND)
        unknown = SqlConnection(id=999999999)
        self.assertEqual(self.client.get(self.detail_url(unknown.hashed_id)).status_code, HTTPStatus.NOT_FOUND)
