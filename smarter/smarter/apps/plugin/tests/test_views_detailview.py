# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.views.detailview`, the plugin manifest page.

The class fixture ``static_plugin`` is owned by the admin user. The page
falls back to the account admin's plugins, and then to the smarter admin's.
"""

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.apps.plugin.urls import PluginReverseNames
from smarter.lib import logging

from .base_classes import STATIC_PLUGIN_NAME, PluginAppTestBase

logger = logging.getLogger(__name__)

OTHER_PLUGIN_NAME = "test_plugin_app_detail_other_account"


class TestPluginDetailView(PluginAppTestBase):
    """
    Test PluginDetailView.

    A second account, with its own plugin, verifies that a user cannot view
    another account's plugins. The TestAccountMixin teardown deletes it.
    """

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

    def test_get(self):
        """Test that the owner gets the plugin's manifest, as yaml."""
        response = self.client.get(self.url(self.static_plugin.plugin_meta))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(STATIC_PLUGIN_NAME, content)
        self.assertIn("Gobstopper", content)

    def test_get_account_admin_plugin(self):
        """Test that a non-admin user gets their account admin's plugin."""
        self.client.force_login(self.non_admin_user)
        response = self.client.get(self.url(self.static_plugin.plugin_meta))
        self.assertEqual(response.status_code, 200)
        self.assertIn(STATIC_PLUGIN_NAME, response.content.decode())

    def test_get_other_account_plugin(self):
        """Test that a user cannot get another account's plugin."""
        response = self.client.get(self.url(self.other_plugin.plugin_meta))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(OTHER_PLUGIN_NAME, response.content.decode())

    def test_get_invalid_hashed_id(self):
        """Test that an invalid plugin identifier is not found."""
        url = reverse(
            f"{PluginReverseNames.namespace}:{PluginReverseNames.detailview}", kwargs={"hashed_id": "not-a-hash"}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user(self):
        """Test that an anonymous user cannot get the page."""
        self.client.logout()
        response = self.client.get(self.url(self.static_plugin.plugin_meta))
        self.assertIn(response.status_code, (302, 404))
        self.assertNotIn("Gobstopper", response.content.decode())
