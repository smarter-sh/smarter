"""
A test mixin for the dashboard views that each resource app repeats: the React list page, its list, clone, delete and rename api, and the manifest detail page.

A subclass names the app's model, url names and url parameter, and creates the resource::

    class TestProviderViews(ResourceViewsTestMixin, TestAccountMixin):
        model = Provider
        reverse_names = ProviderReverseNames
        id_kwarg = "llmclient_id"
        invalidate_cache = staticmethod(invalidate_all_cached_providers_for_user_profile)

        @classmethod
        def create_resource(cls, name):
            return Provider.objects.create(name=name, user_profile=cls.user_profile, base_url="https://x/")

The resource that setUpClass() creates is owned by the account's admin user. Each test that
changes a resource changes a throwaway copy, which is deleted afterwards.
"""

from http import HTTPStatus
from typing import Callable, Optional

from django.db import models
from django.test import Client
from django.urls import reverse

from smarter.lib import json


class ResourceViewsTestMixin:
    """Test the React list page, the list api, the clone, delete and rename apis, and the detail page."""

    model: type[models.Model]
    reverse_names: type
    id_kwarg: str
    invalidate_cache: Optional[Callable] = None
    resource_name_prefix = "test_resource_views"
    detail_view_name = "detailview"

    @classmethod
    def create_resource(cls, name: str) -> models.Model:
        raise NotImplementedError

    @classmethod
    def setUpClass(cls):
        super().setUpClass()  # type: ignore[misc]
        cls.resource = cls.create_resource(f"{cls.resource_name_prefix}_{cls.hash_suffix}")  # type: ignore[attr-defined]

    @classmethod
    def tearDownClass(cls):
        cls.model.objects.filter(name__startswith=cls.resource_name_prefix).delete()  # type: ignore[attr-defined]
        super().tearDownClass()  # type: ignore[misc]

    def setUp(self):
        super().setUp()  # type: ignore[misc]
        self.client = Client()
        self.addCleanup(self.client.logout)  # type: ignore[attr-defined]
        self.client.force_login(self.admin_user)  # type: ignore[attr-defined]
        if self.invalidate_cache:
            self.invalidate_cache(self.user_profile)  # type: ignore[attr-defined,misc]

    # -------------------------------------------------------------------------
    # helpers
    # -------------------------------------------------------------------------
    def url(self, name: str, **kwargs) -> str:
        return reverse(f"{self.reverse_names.namespace}:{getattr(self.reverse_names, name)}", kwargs=kwargs or None)

    def post(self, url: str, status: int = HTTPStatus.OK) -> dict:
        """POST to ``url``, assert the response's status, and return its json."""
        response = self.client.post(url)
        self.assertEqual(response.status_code, status, response.content[:500])  # type: ignore[attr-defined]
        return json.loads(response.content)

    def listed(self, ownership_filter: Optional[str] = None, **params) -> list[str]:
        """Return the names of the resources that the list api returns."""
        if ownership_filter:
            url = self.url("listview_api", ownership_filter=ownership_filter)
        else:
            url = self.url("listview_api_all")
        if params:
            url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
        return [item["name"] for item in self.post(url)["objects"]]

    def throwaway(self, suffix: str) -> models.Model:
        """Return a new resource, which is deleted after the test."""
        name = f"{self.resource_name_prefix}_{suffix}_{self.hash_suffix}"  # type: ignore[attr-defined]
        self.addCleanup(self.model.objects.filter(name__startswith=name).delete)  # type: ignore[attr-defined]
        return self.create_resource(name)

    def id_url(self, name: str, resource_id: int, **kwargs) -> str:
        return self.url(name, **{self.id_kwarg: resource_id}, **kwargs)

    # -------------------------------------------------------------------------
    # the React list page and its list api
    # -------------------------------------------------------------------------
    def test_listview_page(self):
        """Test the React list page, and that an anonymous user is redirected to the login page."""
        self.assertEqual(self.client.get(self.url("listview")).status_code, HTTPStatus.OK)  # type: ignore[attr-defined]
        self.client.logout()
        self.assertEqual(self.client.get(self.url("listview")).status_code, HTTPStatus.FOUND)  # type: ignore[attr-defined]

    def test_list_api(self):
        """Test that the list api returns the user, the smarter admin, and the resource, also for a GET."""
        data = self.post(self.url("listview_api_all"))
        self.assertIn("user", data)  # type: ignore[attr-defined]
        self.assertIn("admin", data)  # type: ignore[attr-defined]
        self.assertIn(self.resource.name, [item["name"] for item in data["objects"]])  # type: ignore[attr-defined]
        response = self.client.get(self.url("listview_api_all"))
        self.assertEqual(response.status_code, HTTPStatus.OK)  # type: ignore[attr-defined]

    def test_list_api_filters(self):
        """Test the owned, shared and all filters, and that invalidate_cache shows a new resource."""
        self.assertIn(self.resource.name, self.listed("owned"))  # type: ignore[attr-defined]
        self.assertNotIn(self.resource.name, self.listed("shared"))  # type: ignore[attr-defined]
        self.assertIn(self.resource.name, self.listed("all"))  # type: ignore[attr-defined]
        resource = self.throwaway("newest")
        self.assertIn(resource.name, self.listed("owned", invalidate_cache="true", page_size=100))  # type: ignore[attr-defined]

    # -------------------------------------------------------------------------
    # the clone, delete and rename apis
    # -------------------------------------------------------------------------
    def test_clone(self):
        """Test that the clone api copies the resource for the user, and that an unknown resource is a 404."""
        resource = self.throwaway("clone_source")
        clone_name = f"{resource.name}_copy"
        data = self.post(self.id_url("listview_api_clone", resource.pk, new_name=clone_name))
        self.assertEqual(data["name"], clone_name)  # type: ignore[attr-defined]
        self.assertTrue(self.model.objects.filter(name=clone_name, user_profile=self.user_profile).exists())  # type: ignore[attr-defined]
        self.post(self.id_url("listview_api_clone", 999999999, new_name="x"), status=HTTPStatus.NOT_FOUND)

    def test_delete(self):
        """Test that the delete api deletes the resource, and that an unknown resource is a 404."""
        resource = self.throwaway("delete")
        self.post(self.id_url("listview_api_delete", resource.pk))
        self.assertFalse(self.model.objects.filter(pk=resource.pk).exists())  # type: ignore[attr-defined]
        self.post(self.id_url("listview_api_delete", 999999999), status=HTTPStatus.NOT_FOUND)

    def test_rename(self):
        """Test that the rename api renames the resource, and that an unknown resource is a 404."""
        resource = self.throwaway("rename")
        new_name = f"{resource.name}_renamed"
        data = self.post(self.id_url("listview_api_rename", resource.pk, new_name=new_name))
        self.assertEqual(data["name"], new_name)  # type: ignore[attr-defined]
        self.assertEqual(self.model.objects.get(pk=resource.pk).name, new_name)  # type: ignore[attr-defined]
        self.post(self.id_url("listview_api_rename", 999999999, new_name="x"), status=HTTPStatus.NOT_FOUND)

    # -------------------------------------------------------------------------
    # the detail page
    # -------------------------------------------------------------------------
    def test_detail(self):
        """Test that the detail page renders the resource's manifest."""
        response = self.client.get(self.url(self.detail_view_name, hashed_id=self.resource.hashed_id))  # type: ignore[attr-defined]
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])  # type: ignore[attr-defined]
        self.assertIn(self.resource.name.encode(), response.content)  # type: ignore[attr-defined]

    def test_detail_not_found(self):
        """Test that an invalid, or unknown, hashed id is a 404."""
        response = self.client.get(self.url(self.detail_view_name, hashed_id="not-a-hashed-id"))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)  # type: ignore[attr-defined]
        unknown = self.model(id=999999999)
        response = self.client.get(self.url(self.detail_view_name, hashed_id=unknown.hashed_id))  # type: ignore[attr-defined]
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)  # type: ignore[attr-defined]
