# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test User."""

# python stuff
import unittest

from django.core.cache import caches


class TestRedis(unittest.TestCase):
    """Test Account model"""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = caches["default"]

    def tearDown(self):
        """Clean up test fixtures."""
        self.cache.clear()

    def test_redis_is_available(self):
        """Test that Redis cache is reachable."""
        self.cache.set("test_key", "test_value")
        result = self.cache.get("test_key")
        self.assertEqual(result, "test_value")
