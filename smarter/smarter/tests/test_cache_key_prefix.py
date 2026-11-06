"""Test that the application's cache keys depend on the Django version."""

import django
from django.conf import settings
from django.core.cache import caches

from smarter.lib.unittest.base_classes import SmarterTestBase


class TestCacheKeyPrefix(SmarterTestBase):
    """
    Pods on two Django versions, during a rolling update, must not share pickled model instances.

    See CACHE_KEY_PREFIX in smarter.settings.base.
    """

    def test_default_cache_keys_contain_the_django_version(self):
        key = caches["default"].make_key("x")
        self.assertIn(f"django{django.__version__}", key)

    def test_session_cache_keys_do_not_contain_the_django_version(self):
        session_cache = caches[settings.SESSION_CACHE_ALIAS]
        key = session_cache.make_key("x")
        self.assertNotIn(django.__version__, key)
