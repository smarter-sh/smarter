# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.llmtool.views.detailview`, the plugin manifest page: the single-page console's, which.

loads the plugin from the dashboard's resource api.

The class fixture ``static_plugin`` is owned by the admin user. A user may read their own plugins, their account
admin's, and the smarter admin's; a superuser may read every plugin.
"""

from http import HTTPStatus

from django.test import Client
from django.urls import get_urlconf, reverse, set_urlconf

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.llmtool.models import PluginMeta
from smarter.apps.llmtool.plugin.static import StaticPlugin
from smarter.apps.llmtool.urls import PluginReverseNames
from smarter.lib import logging
from smarter.lib.unittest.resource_views import (
    assert_console_page,
    assert_no_resource,
    resource_api_url,
    resource_detail_json,
)

from .base_classes import STATIC_PLUGIN_NAME, PluginAppTestBase

logger = logging.getLogger(__name__)

OTHER_PLUGIN_NAME = "test_plugin_app_detail_other_account"


class TestPluginDetailView(PluginAppTestBase):
    """
    Test PluginDetailView.

    A second account, with its own plugin, verifies that a user cannot view
    another account's plugins. The TestAccountMixin teardown deletes it.
    """

    other_admin_user: User
    other_account: Account
    other_user_profile: UserProfile
    other_plugin: StaticPlugin

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_admin_user, cls.other_account, cls.other_user_profile = admin_user_factory()
        cls.other_plugin = StaticPlugin(
            manifest=cls.static_manifest(OTHER_PLUGIN_NAME), user_profile=cls.other_user_profile
        )

    @classmethod
    def tearDownClass(cls):
        PluginMeta.objects.filter(user_profile=cls.other_user_profile).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)

    def url(self, plugin_meta) -> str:
        """Return the detail page's url for a plugin."""
        return reverse(
            f"{PluginReverseNames.namespace}:{PluginReverseNames.detailview}",
            kwargs={"hashed_id": plugin_meta.hashed_id},
        )

    def test_manifest_url(self):
        """Test that PluginMeta.manifest_url is the detail page's url."""
        plugin_meta = self.static_plugin.plugin_meta
        self.assertEqual(plugin_meta.manifest_url, self.url(plugin_meta))  # type: ignore[union-attr]

    def test_manifest_url_from_llmclient_host(self):
        """Test that PluginMeta.manifest_url builds while a deployed LLMClient's urlconf is active, e.g. for a tool call."""
        plugin_meta = self.static_plugin.plugin_meta
        expected = self.url(plugin_meta)
        previous = get_urlconf()
        self.addCleanup(set_urlconf, previous)
        set_urlconf("smarter.urls.llmclients")

        self.assertEqual(plugin_meta.manifest_url, expected)  # type: ignore[union-attr]

    def test_get(self):
        """Test that the manifest page is the console's, whose resource api returns the owner the plugin's manifest."""
        plugin_meta = self.static_plugin.plugin_meta
        detail = resource_detail_json(self, plugin_meta.record_locator)  # type: ignore[union-attr]
        self.assertEqual(detail["name"], STATIC_PLUGIN_NAME)
        self.assertIn(STATIC_PLUGIN_NAME, detail["manifest"] or "")
        self.assertIn("Gobstopper", detail["manifest"] or "")
        assert_console_page(self, self.url(plugin_meta))

    def test_get_account_admin_plugin(self):
        """Test that a non-admin user may read their account admin's plugin."""
        self.client.force_login(self.non_admin_user)
        detail = resource_detail_json(self, self.static_plugin.plugin_meta.record_locator)  # type: ignore[union-attr]
        self.assertIn(STATIC_PLUGIN_NAME, detail["manifest"] or "")

    def test_get_other_account_plugin(self):
        """
        Test that a regular user may not read another account's plugin, and that a superuser, who may read every.

        resource, may.
        """
        other_plugin_meta = self.other_plugin.plugin_meta
        assert other_plugin_meta is not None
        record_locator = other_plugin_meta.record_locator
        self.client.force_login(self.non_admin_user)
        assert_no_resource(self, record_locator)
        self.client.force_login(self.admin_user)
        detail = resource_detail_json(self, record_locator)
        self.assertEqual(detail["name"], OTHER_PLUGIN_NAME)

    def test_get_invalid_hashed_id(self):
        """Test that the resource api has no plugin for an invalid, or unknown, id."""
        assert_no_resource(self, "pluginmeta-not-a-hash")
        assert_no_resource(self, PluginMeta(id=999999999).record_locator)

    def test_anonymous_user(self):
        """Test that the resource api doesn't return the plugin to an anonymous user, whose manifest page is the console's."""
        self.client.logout()
        response = self.client.get(resource_api_url(self.static_plugin.plugin_meta.record_locator))  # type: ignore[union-attr]
        self.assertNotEqual(response.status_code, HTTPStatus.OK)
        self.assertNotIn("Gobstopper", response.content.decode())
        self.assertNotIn(STATIC_PLUGIN_NAME, response.content.decode())
        assert_console_page(self, self.url(self.static_plugin.plugin_meta))
