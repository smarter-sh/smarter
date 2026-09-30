# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.caching`.

The class fixture ``static_plugin`` is owned by the admin user. The non-admin
user belongs to the same account, so the admin user's plugins are shared
with them.
"""

from unittest import mock

from smarter.apps.plugin.caching import (
    get_cached_plugins_available_to_user_profile,
    get_cached_plugins_owned_by_user_profile,
    get_cached_plugins_shared_with_user_profile,
    invalidate_all_cached_plugins_for_user_profile,
    invalidate_cached_plugins_available_to_user_profile,
    invalidate_cached_plugins_owned_by_user_profile,
    invalidate_cached_plugins_shared_with_user_profile,
)
from smarter.lib import logging

from .base_classes import STATIC_PLUGIN_NAME, PluginAppTestBase

logger = logging.getLogger(__name__)

CACHING_MODULE = "smarter.apps.plugin.caching"


class TestPluginCaching(PluginAppTestBase):
    """Test the cached PluginMeta querysets, and their invalidation."""

    def setUp(self):
        super().setUp()
        invalidate_all_cached_plugins_for_user_profile(self.user_profile)
        invalidate_all_cached_plugins_for_user_profile(self.non_admin_user_profile)

    def names(self, qs) -> list[str]:
        """Return the names of the PluginMetas in a queryset."""
        return [plugin_meta.name for plugin_meta in qs]

    def test_owned_by(self):
        """Test that the owner's plugins are owned by them, and not by the non-admin user."""
        self.assertIn(STATIC_PLUGIN_NAME, self.names(get_cached_plugins_owned_by_user_profile(self.user_profile)))
        self.assertNotIn(
            STATIC_PLUGIN_NAME, self.names(get_cached_plugins_owned_by_user_profile(self.non_admin_user_profile))
        )

    def test_shared_with(self):
        """Test that the admin user's plugins are shared with the account's non-admin user, and not with the owner."""
        self.assertIn(
            STATIC_PLUGIN_NAME, self.names(get_cached_plugins_shared_with_user_profile(self.non_admin_user_profile))
        )
        self.assertNotIn(STATIC_PLUGIN_NAME, self.names(get_cached_plugins_shared_with_user_profile(self.user_profile)))

    def test_available_to(self):
        """Test that the admin user's plugins are available to both users."""
        self.assertIn(STATIC_PLUGIN_NAME, self.names(get_cached_plugins_available_to_user_profile(self.user_profile)))
        self.assertIn(
            STATIC_PLUGIN_NAME, self.names(get_cached_plugins_available_to_user_profile(self.non_admin_user_profile))
        )

    def test_invalidate_owned_by(self):
        """Test that invalidation makes a new plugin visible in the owner's plugins."""
        name = "test_plugin_app_caching_owned"
        get_cached_plugins_owned_by_user_profile(self.user_profile)
        self.new_static_plugin(name)
        invalidate_cached_plugins_owned_by_user_profile(self.user_profile)
        self.assertIn(name, self.names(get_cached_plugins_owned_by_user_profile(self.user_profile)))

    def test_invalidate_shared_with(self):
        """Test that invalidation makes a new plugin visible in the plugins shared with the non-admin user."""
        name = "test_plugin_app_caching_shared"
        get_cached_plugins_shared_with_user_profile(self.non_admin_user_profile)
        self.new_static_plugin(name)
        invalidate_cached_plugins_shared_with_user_profile(self.non_admin_user_profile)
        self.assertIn(name, self.names(get_cached_plugins_shared_with_user_profile(self.non_admin_user_profile)))

    def test_invalidate_available_to(self):
        """Test that invalidation makes a new plugin visible in the plugins available to the non-admin user."""
        name = "test_plugin_app_caching_available"
        get_cached_plugins_available_to_user_profile(self.non_admin_user_profile)
        self.new_static_plugin(name)
        invalidate_cached_plugins_available_to_user_profile(self.non_admin_user_profile)
        self.assertIn(name, self.names(get_cached_plugins_available_to_user_profile(self.non_admin_user_profile)))

    def test_invalidate_all(self):
        """Test that invalidate_all_cached_plugins_for_user_profile() invalidates all three caches."""
        with (
            mock.patch(f"{CACHING_MODULE}.invalidate_cached_plugins_owned_by_user_profile") as owned,
            mock.patch(f"{CACHING_MODULE}.invalidate_cached_plugins_shared_with_user_profile") as shared,
            mock.patch(f"{CACHING_MODULE}.invalidate_cached_plugins_available_to_user_profile") as available,
        ):
            invalidate_all_cached_plugins_for_user_profile(self.user_profile)
        owned.assert_called_once_with(user_profile=self.user_profile)
        shared.assert_called_once_with(user_profile=self.user_profile)
        available.assert_called_once_with(user_profile=self.user_profile)

    def test_invalidate_all_after_delete(self):
        """Test that invalidation removes a deleted plugin from every cached queryset."""
        name = "test_plugin_app_caching_deleted"
        self.new_static_plugin(name)
        invalidate_all_cached_plugins_for_user_profile(self.user_profile)
        self.assertIn(name, self.names(get_cached_plugins_owned_by_user_profile(self.user_profile)))
        self.assertIn(name, self.names(get_cached_plugins_available_to_user_profile(self.user_profile)))

        self.delete_plugin_by_name(name)
        invalidate_all_cached_plugins_for_user_profile(self.user_profile)
        self.assertNotIn(name, self.names(get_cached_plugins_owned_by_user_profile(self.user_profile)))
        self.assertNotIn(name, self.names(get_cached_plugins_available_to_user_profile(self.user_profile)))
