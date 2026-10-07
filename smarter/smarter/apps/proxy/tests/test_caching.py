"""Test the cached Proxy querysets, :mod:`smarter.apps.proxy.caching`, and their invalidation by :mod:`smarter.apps.proxy.receivers`."""

from smarter.apps.proxy.caching import (
    get_cached_proxies_available_to_user_profile,
    get_cached_proxies_owned_by_user_profile,
    get_cached_proxies_shared_with_user_profile,
    invalidate_all_cached_proxies_for_user_profile,
)

from .base_classes import ProxyTestBase


def names(queryset) -> set[str]:
    return set(queryset.values_list("name", flat=True))


class TestProxyCaching(ProxyTestBase):
    """Test the owned, shared and available Proxies of a user."""

    def setUp(self):
        super().setUp()
        invalidate_all_cached_proxies_for_user_profile(self.staff_user_profile)
        self.addCleanup(invalidate_all_cached_proxies_for_user_profile, self.staff_user_profile)

    def test_owned_shared_available(self):
        own = self.proxy("test_caching_own", user_profile=self.staff_user_profile)
        account = self.proxy("test_caching_account")
        self.assertIn(own.name, names(get_cached_proxies_owned_by_user_profile(self.staff_user_profile)))
        self.assertNotIn(account.name, names(get_cached_proxies_owned_by_user_profile(self.staff_user_profile)))
        shared = names(get_cached_proxies_shared_with_user_profile(self.staff_user_profile))
        self.assertIn(account.name, shared)
        self.assertNotIn(own.name, shared)
        self.assertTrue(
            {own.name, account.name} <= names(get_cached_proxies_available_to_user_profile(self.staff_user_profile))
        )

    def test_save_invalidates(self):
        """Test that saving and deleting a Proxy invalidates its owner's cached lists."""
        self.assertNotIn("test_caching_new", names(get_cached_proxies_owned_by_user_profile(self.staff_user_profile)))
        proxy = self.proxy("test_caching_new", user_profile=self.staff_user_profile)
        self.assertIn("test_caching_new", names(get_cached_proxies_owned_by_user_profile(self.staff_user_profile)))
        proxy.delete()
        self.assertNotIn("test_caching_new", names(get_cached_proxies_owned_by_user_profile(self.staff_user_profile)))
