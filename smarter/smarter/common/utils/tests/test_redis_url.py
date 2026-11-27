"""Test the Redis url helpers."""

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..redis_url import redis_server_url, redis_url_with_database


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


class TestRedisServerUrl(SmarterTestBase):
    """Test redis_server_url()."""

    def test_default_user(self):
        """Without a username, the url authenticates as Redis's default user."""
        self.assertEqual(redis_server_url("smarter-redis:6379", None, "secret"), "redis://:secret@smarter-redis:6379")

    def test_named_user(self):
        """An ACL user, e.g. the tool worker's, is named before the password."""
        self.assertEqual(
            redis_server_url("smarter-redis:6379", "tools", "secret"), "redis://tools:secret@smarter-redis:6379"
        )

    def test_quotes_reserved_characters(self):
        """A character that a url reserves can't end the credentials early."""
        self.assertEqual(
            redis_server_url("smarter-redis:6379", "us@er", "pa@ss%word/"),
            "redis://us%40er:pa%40ss%25word%2F@smarter-redis:6379",
        )
