"""Test the cached lookups of :class:`smarter.apps.plugin.models.PluginMeta`."""

from unittest.mock import MagicMock, patch

from smarter.apps.account.models import UserProfile
from smarter.apps.api.v1.manifests.enum import SAMKinds
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

    def test_kind_properties(self):
        meta = PluginMeta(plugin_class="static")
        self.assertTrue(meta.is_billable_resource)
        self.assertEqual(meta.kind, SAMKinds.STATIC_PLUGIN)
        self.assertEqual(meta.rfc1034_compliant_kind, meta.kind.value.lower())
        with self.assertRaises(SmarterValueError):
            _ = PluginMeta(plugin_class="nope").kind

    def test_get_cached_object_without_a_user_profile_or_pk(self):
        with patch.object(UserProfile, "get_cached_object", side_effect=UserProfile.DoesNotExist):
            with self.assertRaises(SmarterValueError):
                PluginMeta.get_cached_object(name=STATIC_PLUGIN_NAME)

    def test_get_cached_object_without_a_plugin_class(self):
        meta = self.static_plugin.plugin_meta
        found = PluginMeta.get_cached_object(name=meta.name, user_profile=self.user_profile)
        self.assertEqual(found.pk, meta.pk)

    def test_get_cached_plugins_when_lookups_fail(self):
        """A failed lookup of the user's, admin's or Smarter's plugins contributes none."""
        with patch.object(PluginMeta, "get_cached_objects", side_effect=PluginMeta.DoesNotExist("nope")) as lookup:
            PluginMeta.get_cached_plugins_for_user_profile_id(invalidate=True, user_profile_id=self.user_profile.id)
        self.assertEqual(lookup.call_count, 3)

    def test_get_cached_plugins_skips_duplicate_entries(self):
        plugin = MagicMock(id=1)

        def fake_cache_results(*args, **kwargs):
            return lambda fn: lambda *a, **kw: [plugin, plugin]

        with patch("smarter.apps.plugin.models.plugin_meta.cache_results", fake_cache_results):
            plugins = PluginMeta.get_cached_plugins_for_user_profile_id(user_profile_id=self.user_profile.id)
        self.assertEqual(plugins, [plugin])
