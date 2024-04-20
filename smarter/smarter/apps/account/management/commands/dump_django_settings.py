"""This module is used to add an email address to the Account Contact list."""

from django.conf import settings
from django.core.management.base import BaseCommand


# pylint: disable=E1101
class Command(BaseCommand):
    """add an email address to the Account Contact list."""

    def handle(self, *args, **options):
        """Dump all Django settings."""

        for setting in dir(settings):
            if setting.isupper():
                print(f"{setting}: {getattr(settings, setting)}")
