# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test API end points."""

# python stuff
import os
import unittest

from django.contrib.auth.models import User

# our stuff
from smarter.apps.account.tests.test_setup import PROJECT_ROOT


PLUGINS_PATH = os.path.join(PROJECT_ROOT, "smarter", "app", "plugins", "data", "sample-plugins")


class TestUrls(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

    user: User

    def setUp(self):
        """Set up test fixtures."""
        self.user, _ = User.objects.get_or_create(username="testuser", password="12345")

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()

    def test_create(self):
        """Test that we can create an account."""
