"""This module is used to initialize Wagtail CMS."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py initialize_wagtail command. This module is used to initialize Wagtail CMS."""

    help = "Initializes Wagtail."

    def handle(self, *args, **options):

        call_command("preseed_transfer_table", "wagtailcore.page")
        self.stdout.write(self.style.SUCCESS("initialize_wagtail"))
