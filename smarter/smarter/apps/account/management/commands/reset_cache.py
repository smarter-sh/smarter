"""
Django management command to reset the Django cache.

This module defines the ``reset_cache`` management command for the Smarter platform.
It provides a mechanism to clear (reset) all entries from the Django cache backend being used.

Features
--------
- Clears all cache entries for the configured Django cache backend.
- Outputs status messages upon success or failure.

Typical Usage
-------------
Used by administrators or developers via ``manage.py reset_cache`` to manually reset cached data,
which can be helpful during development, troubleshooting, or after certain operational events.
"""

from django.core.cache import cache

from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py command to reset the Django cache."""

    def handle(self, *args, **options):
        """Reset the Django cache."""
        self.handle_begin()

        # Add logic to reset the Django cache here
        try:
            cache.clear()  # Clear the cache
        # pylint: disable=broad-except
        except Exception as e:
            self.handle_completed_failure(msg=f"reset_cache command failed with error: {e}")
            return

        self.handle_completed_success(msg="reset_cache command completed successfully.")
