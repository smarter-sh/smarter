"""Test the proxy app's web console views, :mod:`smarter.apps.proxy.views`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.proxy.api.web.urls import ProxyApiWebReverseNames as WebNames
from smarter.apps.proxy.caching import invalidate_all_cached_proxies_for_user_profile
from smarter.apps.proxy.models import Proxy
from smarter.apps.proxy.urls import ProxyReverseNames as Names
from smarter.lib import json
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.resource_views import (
    ResourceViewsTestMixin,
    assert_console_page,
    assert_no_resource,
    resource_detail_json,
)

from .base_classes import API_KEY, ProxyTestBase


def url(name: str, **kwargs) -> str:
    """Return the url of a proxy app view."""
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs)


def web_url(name: str, **kwargs) -> str:
    """Return the url of a proxy app endpoint in the web console's api."""
    return reverse(f"{WebNames.namespace}:{name}", kwargs=kwargs or None)


class TestProxyListApi(ProxyTestBase):
    """Test the React list view's API: list, clone, rename and delete."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.staff_user)
        self.addCleanup(self.client.logout)

    def post(self, path: str, status: int = HTTPStatus.OK) -> SmarterDictType:
        response = self.client.post(path)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content)

    def test_urls(self):
        """Test the action URLs that the React toolbar builds: e.g. clone/<id>/<name>/, not listview/clone/..."""
        self.assertEqual(url(Names.listview), "/proxy/")
        self.assertEqual(web_url(WebNames.listview_all), "/api/web/proxy/listview/")
        self.assertEqual(web_url(WebNames.listview, ownership_filter="owned"), "/api/web/proxy/listview/owned/")
        self.assertEqual(web_url(WebNames.clone, proxy_id=1, new_name="x"), "/api/web/proxy/clone/1/x/")
        self.assertEqual(web_url(WebNames.rename, proxy_id=1, new_name="x"), "/api/web/proxy/rename/1/x/")
        self.assertEqual(web_url(WebNames.delete, proxy_id=1), "/api/web/proxy/delete/1/")
        self.assertEqual(url(Names.detailview, hashed_id="abc"), "/proxy/proxies/abc/")

    def test_list(self):
        """Test that each object has the fields that the React app displays, and never the API key."""
        account_proxy = self.proxy("test_views_list_account")
        own = self.proxy(
            "test_views_list_own",
            user_profile=self.staff_user_profile,
            headers={"anthropic-version": "2023-06-01", "OpenAI-Beta": "v2"},
        )
        response = self.client.post(web_url(WebNames.listview_all))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertNotIn(API_KEY, response.content.decode())
        objects = {item["name"]: item for item in json.loads(response.content)["objects"]}
        self.assertIn(account_proxy.name, objects)
        item = objects[own.name]
        # the list API's JSON is camelCase, as smarter-proxy-list's Proxy type expects.
        for field in (
            "id",
            "hashedId",
            "name",
            "description",
            "userProfile",
            "provider",
            "providerName",
            "apiKeySecret",
            "apiKeySecretName",
            "baseUrl",
            "upstreamUrl",
            "authHeader",
            "authScheme",
            "headers",
            "allowedPaths",
            "timeout",
            "isActive",
            "url",
            "manifestUrl",
            "createdAt",
            "updatedAt",
            "tags",
            "annotations",
            "version",
        ):
            self.assertIn(field, item)
        self.assertEqual(item["providerName"], self.provider.name)
        self.assertEqual(item["apiKeySecretName"], self.secret.name)
        self.assertEqual(item["url"], "/api/v1/proxy/test_views_list_own/")
        self.assertEqual(item["manifestUrl"], own.manifest_url)
        # header names are data, and are not camelCased.
        self.assertEqual(item["headers"], {"anthropic-version": "2023-06-01", "OpenAI-Beta": "v2"})
        owned = self.post(web_url(WebNames.listview, ownership_filter="owned"))
        self.assertEqual([item["name"] for item in owned["objects"]], [own.name])
        shared = self.post(web_url(WebNames.listview, ownership_filter="shared"))
        self.assertIn(account_proxy.name, [item["name"] for item in shared["objects"]])
        self.assertNotIn(own.name, [item["name"] for item in shared["objects"]])

    def test_clone_rename_delete(self):
        """Test the toolbar's actions.

        The scaffold's routes passed llmclient_id, so each one returned 400.
        """
        proxy = self.proxy("test_views_actions", user_profile=self.staff_user_profile, timeout=42)
        clone = self.post(web_url(WebNames.clone, proxy_id=proxy.pk, new_name="test_views_actions_clone"))
        self.addCleanup(Proxy.objects.filter(pk=clone["id"]).delete)
        cloned = Proxy.objects.get(pk=clone["id"])
        self.assertEqual(
            (cloned.name, cloned.timeout, cloned.user_profile),
            ("test_views_actions_clone", 42, self.staff_user_profile),
        )
        renamed = self.post(web_url(WebNames.rename, proxy_id=clone["id"], new_name="test_views_actions_renamed"))
        self.assertEqual(renamed["name"], "test_views_actions_renamed")
        self.post(web_url(WebNames.delete, proxy_id=clone["id"]))
        self.assertFalse(Proxy.objects.filter(pk=clone["id"]).exists())

    def test_clone_builtin(self):
        """Test that a built-in Proxy can be cloned into the user's own."""
        builtin = self.proxy("test_views_builtin", user_profile=smarter_cached_objects.smarter_admin_user_profile)
        clone = self.post(web_url(WebNames.clone, proxy_id=builtin.pk, new_name="test_views_builtin_clone"))
        self.addCleanup(Proxy.objects.filter(pk=clone["id"]).delete)
        self.assertEqual(Proxy.objects.get(pk=clone["id"]).user_profile, self.staff_user_profile)

    def test_not_found(self):
        self.post(web_url(WebNames.delete, proxy_id=999999999), status=HTTPStatus.NOT_FOUND)
        self.post(web_url(WebNames.rename, proxy_id=999999999, new_name="x"), status=HTTPStatus.NOT_FOUND)
        self.post(web_url(WebNames.clone, proxy_id=999999999, new_name="x"), status=HTTPStatus.NOT_FOUND)

    def test_unauthenticated(self):
        self.client.logout()
        response = self.client.post(web_url(WebNames.listview_all))
        self.assertNotEqual(response.status_code, HTTPStatus.OK)


class TestProxyDetailView(ProxyTestBase):
    """Test the manifest page: the console's, which loads the proxy from the dashboard's resource api."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def test_detail(self):
        """Test that the resource api returns the proxy's manifest, without its api key, and the page is the console's."""
        proxy = self.proxy("test_views_detail")
        detail = resource_detail_json(self, proxy.record_locator)
        manifest = detail["manifest"] or ""
        self.assertIn("test_views_detail", manifest)
        self.assertIn("kind: Proxy", manifest)
        self.assertNotIn(API_KEY, json.dumps(detail))
        assert_console_page(self, proxy.manifest_url)

    def test_not_found(self):
        """Test that the resource api has no proxy for an invalid, or unknown, id."""
        assert_no_resource(self, "proxy-not-a-hashed-id")
        assert_no_resource(self, Proxy(id=999999999).record_locator)


class TestProxyResourceViews(ResourceViewsTestMixin, ProxyTestBase):
    """Test the Proxy list page, list, clone, delete and rename apis, and detail page with the shared mixin."""

    model = Proxy
    reverse_names = Names
    web_reverse_names = WebNames
    id_kwarg = "proxy_id"
    invalidate_cache = staticmethod(invalidate_all_cached_proxies_for_user_profile)
    resource_name_prefix = "test_proxy_resource_views"

    @classmethod
    def create_resource(cls, name: str) -> Proxy:
        return cls.create_proxy(name)
