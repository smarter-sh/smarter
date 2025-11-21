"""This module is used to add an email address to the Account Contact list."""

from django.conf import settings

from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """add an email address to the Account Contact list."""

    def handle(self, *args, **options):
        """Dump all Django settings."""
        self.handle_begin()

        for setting in dir(settings):
            if setting.isupper():
                print(f"{setting}: {getattr(settings, setting)}")

        self.handle_completed_success()
