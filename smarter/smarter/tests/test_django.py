# pylint: disable=wrong-import-position
"""Test User."""

import django
from django.conf import settings
from django.utils.version import get_main_version

from smarter.lib.unittest.base_classes import SmarterTestBase


class TestDjango(SmarterTestBase):
    """Test Account model"""

    def test_django_is_installed(self):
        """Test that Celery is running."""
        self.assertIsNotNone(django)

    def test_django_version(self):
        """Test that Django version is correct."""
        main_version = int(get_main_version().split(".", maxsplit=1)[0])
        self.assertGreaterEqual(main_version, 5)

    def test_django_is_configured(self):
        """Test that Django is configured."""
        try:
            self.assertTrue(settings.configured)
        except ImportError:
            self.fail("Django is not configured")
