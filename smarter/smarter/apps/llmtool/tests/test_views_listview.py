# pylint: disable=wrong-import-position
"""Test :mod:`smarter.apps.llmtool.views.listview.view`, the React plugin list page."""

from django.test import Client

from smarter.apps.llmtool.api.web.urls import PluginApiWebReverseNames
from smarter.apps.llmtool.urls import PluginReverseNames
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.resource_views import assert_console_page

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
        """Test that the page is the single-page console's, at /llm-tools/, for anyone."""
        self.assertEqual(self.url, "/llm-tools/")
        self.client.force_login(self.admin_user)
        assert_console_page(self, self.url)

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
        """Test that an anonymous user gets the console's page, which sends them to its sign-in page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
