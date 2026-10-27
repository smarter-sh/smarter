"""Test the Redis url helpers."""

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..redis_url import redis_url_with_database


class TestRedisUrlWithDatabase(SmarterTestBase):
    """Test redis_url_with_database()."""

    def test_replaces_the_database(self):
        self.assertEqual(
            redis_url_with_database("redis://:secret@smarter-redis:6379/1", 2), "redis://:secret@smarter-redis:6379/2"
        )

    def test_adds_a_database_to_a_url_without_one(self):
        self.assertEqual(redis_url_with_database("redis://smarter-redis:6379", 2), "redis://smarter-redis:6379/2")

    def test_keeps_the_query_string(self):
        self.assertEqual(
            redis_url_with_database("rediss://user:pw@host:6380/0?ssl_cert_reqs=none", 2),
            "rediss://user:pw@host:6380/2?ssl_cert_reqs=none",
        )
