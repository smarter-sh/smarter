"""
This module provides a Django management command to print out all Django settings.

(key and value pairs) currently loaded for the running project.

Classes
=======
Command
    Implements the logic for the ``manage.py dump_django_settings`` command.

Functionality
=============
- Iterates through all attributes of the Django ``settings`` object.
- Prints settings where the attribute name is all uppercase (standard for Django settings).
- Can be used for debugging or environment introspection.

Usage Example
=============
    python manage.py dump_django_settings
"""

from django.conf import settings

from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Add an email address to the Account Contact list."""

    def handle(self, *args, **options):
        """Dump all Django settings."""
        self.handle_begin()

        for setting in dir(settings):
            if setting.isupper():
                print(f"{setting}: {getattr(settings, setting)}")

        self.handle_completed_success()
