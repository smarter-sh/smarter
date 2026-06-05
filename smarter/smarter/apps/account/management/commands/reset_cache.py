"""
Django manage.py command to reset the Django cache.
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
