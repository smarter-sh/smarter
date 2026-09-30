# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.views.listview.api`, the React plugin list's api.

The class fixture ``static_plugin`` is owned by the admin user, and shared
with the account's non-admin user.
"""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.plugin.caching import invalidate_all_cached_plugins_for_user_profile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.urls import PluginReverseNames
from smarter.lib import json, logging

from .base_classes import STATIC_PLUGIN_NAME, PluginAppTestBase

logger = logging.getLogger(__name__)

NAMESPACE = PluginReverseNames.namespace


class TestPluginListApiViews(PluginAppTestBase):
    """Test the list, clone, delete and rename api views."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)
        invalidate_all_cached_plugins_for_user_profile(self.user_profile)
        invalidate_all_cached_plugins_for_user_profile(self.non_admin_user_profile)

    def post(self, url: str, status: int = HTTPStatus.OK) -> dict:
        """POST to ``url``, assert the response's status, and return its json."""
        response = self.client.post(url)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content)

    def list_url(self, ownership_filter=None, **params) -> str:
        """Return the list api's url, for an ownership filter and query parameters."""
        if ownership_filter:
            url = reverse(
                f"{NAMESPACE}:{PluginReverseNames.listview_api}", kwargs={"ownership_filter": ownership_filter}
            )
        else:
            url = reverse(f"{NAMESPACE}:{PluginReverseNames.listview_api_all}")
        if params:
            url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
        return url

    def listed(self, ownership_filter=None, **params) -> list[str]:
        """Return the names of the plugins that the list api returns."""
        data = self.post(self.list_url(ownership_filter, **params))
        return [plugin["name"] for plugin in data["objects"]]

    # -------------------------------------------------------------------------
    # PluginListApiView
    # -------------------------------------------------------------------------
    def test_list(self):
        """Test that the list api returns the user, the smarter admin user, and the plugins."""
        data = self.post(self.list_url())
        self.assertIn("user", data)
        self.assertIn("admin", data)
        self.assertIn(STATIC_PLUGIN_NAME, [plugin["name"] for plugin in data["objects"]])

    def test_list_owned(self):
        """Test the owned filter."""
        self.assertIn(STATIC_PLUGIN_NAME, self.listed("owned"))
        self.client.force_login(self.non_admin_user)
        self.assertNotIn(STATIC_PLUGIN_NAME, self.listed("owned"))

    def test_list_shared(self):
        """Test the shared filter."""
        self.assertNotIn(STATIC_PLUGIN_NAME, self.listed("shared"))
        self.client.force_login(self.non_admin_user)
        self.assertIn(STATIC_PLUGIN_NAME, self.listed("shared"))

    def test_list_all(self):
        """Test the all filter."""
        self.assertIn(STATIC_PLUGIN_NAME, self.listed("all"))
        self.client.force_login(self.non_admin_user)
        self.assertIn(STATIC_PLUGIN_NAME, self.listed("all"))

    def test_list_pagination(self):
        """Test that the list api paginates, most recently updated first."""
        name = "test_plugin_app_api_newest"
        self.new_static_plugin(name)
        self.assertEqual(self.listed("owned", page_size=1, invalidate_cache="true"), [name])
        self.assertEqual(self.listed("owned", page_size=1, page=2), [STATIC_PLUGIN_NAME])

    def test_list_invalidate_cache(self):
        """Test that invalidate_cache makes a new plugin visible."""
        name = "test_plugin_app_api_invalidate"
        self.listed("owned")
        self.new_static_plugin(name)
        self.assertIn(name, self.listed("owned", invalidate_cache="true"))

    def test_list_anonymous_user(self):
        """Test that an anonymous user is redirected to the login page."""
        self.client.logout()
        response = self.client.post(self.list_url())
        self.assertEqual(response.status_code, 302)

    # -------------------------------------------------------------------------
    # PluginListApiCloneView
    # -------------------------------------------------------------------------
    def test_clone(self):
        """Test that the clone api creates a complete, usable copy of the plugin."""
        clone_name = "test_plugin_app_api_clone"
        self.addCleanup(self.delete_plugin_by_name, clone_name)
        url = reverse(
            f"{NAMESPACE}:{PluginReverseNames.listview_api_clone}",
            kwargs={"llmclient_id": self.static_plugin.id, "new_name": clone_name},
        )
        data = self.post(url)
        self.assertEqual(data["name"], clone_name)

        clone = PluginMeta.objects.get(name=clone_name, user_profile=self.user_profile)
        plugin = PluginController(user_profile=self.user_profile, plugin_meta=clone).plugin
        self.assertTrue(plugin.ready)
        self.assertEqual(plugin.plugin_data.static_data, self.static_plugin.plugin_data.static_data)  # type: ignore
        self.assertEqual(plugin.plugin_selector.search_terms, self.static_plugin.plugin_selector.search_terms)  # type: ignore

    def test_clone_shared_plugin(self):
        """Test that a user can clone a plugin shared with them, which they then own."""
        clone_name = "test_plugin_app_api_shared_clone"
        self.addCleanup(self.delete_plugin_by_name, clone_name)
        self.client.force_login(self.non_admin_user)
        url = reverse(
            f"{NAMESPACE}:{PluginReverseNames.listview_api_clone}",
            kwargs={"llmclient_id": self.static_plugin.id, "new_name": clone_name},
        )
        self.post(url)
        clone = PluginMeta.objects.get(name=clone_name)
        self.assertEqual(clone.user_profile, self.non_admin_user_profile)
        plugin = PluginController(user_profile=self.non_admin_user_profile, plugin_meta=clone).plugin
        self.assertTrue(plugin.ready)

    def test_clone_not_found(self):
        """Test that the clone api returns 404 for a plugin that does not exist."""
        url = reverse(
            f"{NAMESPACE}:{PluginReverseNames.listview_api_clone}", kwargs={"llmclient_id": 999999999, "new_name": "x"}
        )
        self.post(url, status=HTTPStatus.NOT_FOUND)

    # -------------------------------------------------------------------------
    # PluginListApiRenameView
    # -------------------------------------------------------------------------
    def test_rename(self):
        """Test that the rename api renames the plugin, in snake case."""
        plugin = self.new_static_plugin("test_plugin_app_api_rename")
        self.addCleanup(self.delete_plugin_by_name, "test_plugin_app_api_renamed")
        url = reverse(
            f"{NAMESPACE}:{PluginReverseNames.listview_api_rename}",
            kwargs={"llmclient_id": plugin.id, "new_name": "testPluginAppApiRenamed"},
        )
        data = self.post(url)
        self.assertEqual(data["name"], "test_plugin_app_api_renamed")
        self.assertEqual(PluginMeta.objects.get(id=plugin.id).name, "test_plugin_app_api_renamed")

    def test_rename_not_owner(self):
        """Test that a user cannot rename a plugin that is only shared with them."""
        self.client.force_login(self.non_admin_user)
        url = reverse(
            f"{NAMESPACE}:{PluginReverseNames.listview_api_rename}",
            kwargs={"llmclient_id": self.static_plugin.id, "new_name": "stolen"},
        )
        self.post(url, status=HTTPStatus.NOT_FOUND)
        self.assertEqual(PluginMeta.objects.get(id=self.static_plugin.id).name, STATIC_PLUGIN_NAME)

    # -------------------------------------------------------------------------
    # PluginListApiDeleteView
    # -------------------------------------------------------------------------
    def test_delete(self):
        """Test that the delete api deletes the plugin."""
        plugin = self.new_static_plugin("test_plugin_app_api_delete")
        url = reverse(f"{NAMESPACE}:{PluginReverseNames.listview_api_delete}", kwargs={"llmclient_id": plugin.id})
        self.post(url)
        self.assertFalse(PluginMeta.objects.filter(id=plugin.id).exists())
        self.assertNotIn("test_plugin_app_api_delete", self.listed("owned"))

    def test_delete_not_owner(self):
        """Test that a user cannot delete a plugin that is only shared with them."""
        self.client.force_login(self.non_admin_user)
        url = reverse(
            f"{NAMESPACE}:{PluginReverseNames.listview_api_delete}", kwargs={"llmclient_id": self.static_plugin.id}
        )
        self.post(url, status=HTTPStatus.NOT_FOUND)
        self.assertTrue(PluginMeta.objects.filter(id=self.static_plugin.id).exists())
