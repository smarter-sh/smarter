# pylint: disable=wrong-import-position
"""Test :mod:`smarter.apps.llmtool.urls`."""

from http import HTTPStatus

from django.test import Client
from django.urls import resolve, reverse

from smarter.apps.llmtool.const import namespace
from smarter.apps.llmtool.urls import PluginReverseNames
from smarter.apps.llmtool.views.detailview import PluginDetailView
from smarter.apps.llmtool.views.listview.api import (
    PluginListApiCloneView,
    PluginListApiDeleteView,
    PluginListApiExtensionsView,
    PluginListApiRenameView,
    PluginListApiView,
)
from smarter.apps.llmtool.views.listview.view import PluginListView
from smarter.lib import logging
from smarter.lib.unittest.base_classes import SmarterTestBase

logger = logging.getLogger(__name__)


class TestPluginUrls(SmarterTestBase):
    """Test that each of the plugin app's reverse names resolves to its view."""

    def assertResolves(self, name: str, view_class, kwargs=None):
        """Assert that reversing, and then resolving, ``name`` returns ``view_class`` and ``kwargs``."""
        url = reverse(f"{PluginReverseNames.namespace}:{name}", kwargs=kwargs)
        match = resolve(url)
        self.assertIs(match.func.view_class, view_class, url)  # type: ignore[attr-defined]
        self.assertEqual(match.namespace, namespace)
        for key, value in (kwargs or {}).items():
            self.assertEqual(match.kwargs[key], value, url)
        return url

    def test_namespace(self):
        """Test the app's namespace."""
        self.assertEqual(PluginReverseNames.namespace, "llmtool")

    def test_listview(self):
        """Test the React plugin list page."""
        url = self.assertResolves(PluginReverseNames.listview, PluginListView)
        self.assertEqual(url, "/llm-tools/")

    def test_listview_api_all(self):
        """Test the list api, without an ownership filter."""
        self.assertResolves(PluginReverseNames.listview_api_all, PluginListApiView)

    def test_listview_api(self):
        """Test the list api, with each ownership filter."""
        for ownership_filter in ("owned", "shared", "all"):
            self.assertResolves(
                PluginReverseNames.listview_api, PluginListApiView, kwargs={"ownership_filter": ownership_filter}
            )

    def test_listview_api_clone(self):
        """Test the clone api."""
        self.assertResolves(
            PluginReverseNames.listview_api_clone,
            PluginListApiCloneView,
            kwargs={"llmclient_id": 1, "new_name": "a_clone"},
        )

    def test_listview_api_delete(self):
        """Test the delete api."""
        self.assertResolves(PluginReverseNames.listview_api_delete, PluginListApiDeleteView, kwargs={"llmclient_id": 1})

    def test_listview_api_extensions(self):
        """Test the read-only api of the Extensions tab."""
        url = self.assertResolves(PluginReverseNames.listview_api_extensions, PluginListApiExtensionsView)
        self.assertEqual(url, "/llm-tools/react-integration/api/listview/extensions/")

    def test_listview_api_rename(self):
        """Test the rename api."""
        self.assertResolves(
            PluginReverseNames.listview_api_rename,
            PluginListApiRenameView,
            kwargs={"llmclient_id": 1, "new_name": "a_name"},
        )

    def test_detailview(self):
        """Test the plugin manifest page."""
        url = self.assertResolves(PluginReverseNames.detailview, PluginDetailView, kwargs={"hashed_id": "abc123"})
        self.assertEqual(url, "/llm-tools/plugins/abc123/")

    def test_old_plugin_urls_redirect(self):
        """Test that the pages' old urls, under /plugin/, redirect permanently to /llm-tools/, with their query."""
        for old, new in (
            ("/plugin/", "/llm-tools/"),
            ("/plugin/plugins/abc123/?a=1", "/llm-tools/plugins/abc123/?a=1"),
        ):
            with self.subTest(url=old):
                response = Client().get(old)
                self.assertEqual(response.status_code, HTTPStatus.MOVED_PERMANENTLY)
                self.assertEqual(response["Location"], new)
