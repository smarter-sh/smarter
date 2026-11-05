# pylint: disable=wrong-import-position
"""Test :mod:`smarter.apps.llmtool.urls` and :mod:`smarter.apps.llmtool.api.web.urls`."""

from http import HTTPStatus

from django.test import Client
from django.urls import resolve, reverse

from smarter.apps.llmtool.api.web.urls import PluginApiWebReverseNames
from smarter.apps.llmtool.extension.api.web.urls import ExtensionApiWebReverseNames
from smarter.apps.llmtool.extension.views import (
    ExtensionEnableApiView,
    ExtensionListApiView,
)
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

    def assertResolves(self, name: str, view_class, reverse_names: type = PluginReverseNames, kwargs=None):
        """Assert that reversing, and then resolving, ``name`` returns ``view_class`` and ``kwargs``."""
        url = reverse(f"{reverse_names.namespace}:{name}", kwargs=kwargs)
        match = resolve(url)
        self.assertIs(match.func.view_class, view_class, url)  # type: ignore[attr-defined]
        self.assertEqual(match.namespace, reverse_names.namespace)
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

    def test_web_namespace(self):
        """Test the namespace of the app's endpoints in the web console's api."""
        self.assertEqual(PluginApiWebReverseNames.namespace, "api:web:llmtool")

    def test_web_listview_all(self):
        """Test the list api, without an ownership filter."""
        url = self.assertResolves(PluginApiWebReverseNames.listview_all, PluginListApiView, PluginApiWebReverseNames)
        self.assertEqual(url, "/api/web/llmtool/listview/")

    def test_web_listview(self):
        """Test the list api, with each ownership filter."""
        for ownership_filter in ("owned", "shared", "all"):
            url = self.assertResolves(
                PluginApiWebReverseNames.listview,
                PluginListApiView,
                PluginApiWebReverseNames,
                kwargs={"ownership_filter": ownership_filter},
            )
            self.assertEqual(url, f"/api/web/llmtool/listview/{ownership_filter}/")

    def test_web_clone(self):
        """Test the clone api."""
        url = self.assertResolves(
            PluginApiWebReverseNames.clone,
            PluginListApiCloneView,
            PluginApiWebReverseNames,
            kwargs={"llmclient_id": 1, "new_name": "a_clone"},
        )
        self.assertEqual(url, "/api/web/llmtool/clone/1/a_clone/")

    def test_web_delete(self):
        """Test the delete api."""
        url = self.assertResolves(
            PluginApiWebReverseNames.delete,
            PluginListApiDeleteView,
            PluginApiWebReverseNames,
            kwargs={"llmclient_id": 1},
        )
        self.assertEqual(url, "/api/web/llmtool/delete/1/")

    def test_web_listview_extensions(self):
        """Test the read-only api of the Extensions tab, which the React app builds from the list api's url."""
        url = self.assertResolves(
            PluginApiWebReverseNames.listview_extensions, PluginListApiExtensionsView, PluginApiWebReverseNames
        )
        self.assertEqual(url, "/api/web/llmtool/listview/extensions/")

    def test_web_rename(self):
        """Test the rename api."""
        url = self.assertResolves(
            PluginApiWebReverseNames.rename,
            PluginListApiRenameView,
            PluginApiWebReverseNames,
            kwargs={"llmclient_id": 1, "new_name": "a_name"},
        )
        self.assertEqual(url, "/api/web/llmtool/rename/1/a_name/")

    def test_web_extensions_root(self):
        """Test the Extensions pages' api, which is nested under the app's endpoints."""
        url = self.assertResolves(ExtensionApiWebReverseNames.root, ExtensionListApiView, ExtensionApiWebReverseNames)
        self.assertEqual(url, "/api/web/llmtool/extensions/")
        url = self.assertResolves(
            ExtensionApiWebReverseNames.enable,
            ExtensionEnableApiView,
            ExtensionApiWebReverseNames,
            kwargs={"slug": "echo"},
        )
        self.assertEqual(url, "/api/web/llmtool/extensions/echo/enable/")

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
