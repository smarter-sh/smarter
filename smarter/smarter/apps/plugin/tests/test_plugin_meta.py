"""Test the cached lookups of :class:`smarter.apps.plugin.models.PluginMeta`."""

from smarter.apps.plugin.models import PluginMeta
from smarter.common.exceptions import SmarterValueError

from .base_classes import STATIC_PLUGIN_NAME, PluginAppTestBase


class TestPluginMetaLookups(PluginAppTestBase):
    """Test PluginMeta.get_cached_object() and get_cached_plugins_for_user_profile_id()."""

    def test_get_cached_object_by_plugin_class(self):
        meta = self.static_plugin.plugin_meta
        for invalidate in (True, False):
            found = PluginMeta.get_cached_object(
                invalidate=invalidate, name=meta.name, user_profile=self.user_profile, plugin_class=meta.plugin_class
            )
            self.assertEqual(found.pk, meta.pk)
        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.get_cached_object(
                name="no_such_plugin", user_profile=self.user_profile, plugin_class=meta.plugin_class
            )

    def test_get_cached_object_by_user(self):
        """Test the lookup by the user, or the username, and account, rather than the user profile."""
        meta = self.static_plugin.plugin_meta
        found = PluginMeta.get_cached_object(name=meta.name, user=self.admin_user, account=self.account)
        self.assertEqual(found.pk, meta.pk)
        found = PluginMeta.get_cached_object(name=meta.name, username=self.admin_user.username, account=self.account)
        self.assertEqual(found.pk, meta.pk)
        self.assertEqual(PluginMeta.get_cached_object(pk=meta.pk).pk, meta.pk)

    def test_get_cached_object_requires_pk_or_user(self):
        """Test that a lookup by an unknown username is refused with SmarterValueError."""
        with self.assertRaises(SmarterValueError):
            PluginMeta.get_cached_object(name=STATIC_PLUGIN_NAME, username="no_such_user", account=self.account)

    def test_get_cached_plugins_for_user_profile_id(self):
        """Test that a user's plugins include their account admin's, and that an unknown user profile has none."""
        meta = self.static_plugin.plugin_meta
        for user_profile in (self.user_profile, self.non_admin_user_profile):
            with self.subTest(user_profile=user_profile):
                plugins = PluginMeta.get_cached_plugins_for_user_profile_id(
                    invalidate=True, user_profile_id=user_profile.id
                )
                self.assertIn(meta.pk, [plugin.pk for plugin in plugins])
        self.assertEqual(PluginMeta.get_cached_plugins_for_user_profile_id(user_profile_id=999999999), [])
