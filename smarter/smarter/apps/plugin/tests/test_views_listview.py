# pylint: disable=wrong-import-position
"""Test :mod:`smarter.apps.plugin.views.listview.view`, the React plugin list page."""

from django.test import Client

from smarter.apps.plugin.urls import PluginReverseNames
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse

from .base_classes import PluginAppTestBase

logger = logging.getLogger(__name__)


class TestPluginListView(PluginAppTestBase):
    """Test PluginListView."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.url = reverse(PluginReverseNames.namespace, PluginReverseNames.listview)

    def test_get(self):
        """Test that an authenticated user gets the React app's root and configuration."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        plugin_list = response.context["plugin_list"]
        self.assertEqual(plugin_list["root_id"], "smarter-plugin-list-root")
        self.assertEqual(
            plugin_list["plugin_list_api_url"],
            reverse(PluginReverseNames.namespace, PluginReverseNames.listview_api_all),
        )
        for key in ("django_csrf_cookie_name", "django_session_cookie_name", "react_debug_mode", "smarter_request_id"):
            self.assertIn(key, plugin_list)
        self.assertIn("smarter-plugin-list-root", response.content.decode())

    def test_get_non_admin_user(self):
        """Test that a non-admin user gets the page."""
        self.client.force_login(self.non_admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_never_cached(self):
        """Test that the page is never cached."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)
        self.assertIn("no-cache", response.get("Cache-Control", ""))

    def test_anonymous_user(self):
        """Test that an anonymous user is redirected to the login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])
