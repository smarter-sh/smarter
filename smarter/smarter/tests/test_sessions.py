"""Test that user sessions are kept apart from the application's cache."""

from importlib import import_module

from django.conf import settings
from django.core.cache import cache

from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSessionsSurviveCacheClear(SmarterTestBase):
    """Cache.clear(), e.g. from manage.py reset_cache, must not log users out."""

    def test_a_session_survives_cache_clear(self):
        store = import_module(settings.SESSION_ENGINE).SessionStore()
        store["user"] = "test_sessions"
        store.create()
        self.addCleanup(store.delete)

        cache.set("test_sessions_key", "value")
        cache.clear()

        self.assertIsNone(cache.get("test_sessions_key"))
        self.assertTrue(store.exists(store.session_key))
        loaded = import_module(settings.SESSION_ENGINE).SessionStore(session_key=store.session_key)
        self.assertEqual(loaded["user"], "test_sessions")
