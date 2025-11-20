"""This module is used to initialize Wagtail CMS."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py initialize_wagtail command. This module is used to initialize Wagtail CMS."""

    help = "Initializes Wagtail."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("smarter.apps.cms.management.commands.initialize_wagtail started."))

        try:
            call_command("preseed_transfer_table", "wagtailcore.page")
        # pylint: disable=broad-except
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Error preseeding transfer table: {exc}"))
            self.stdout.write(
                self.style.ERROR("smarter.apps.cms.management.commands.initialize_wagtail completed with errors.")
            )
            return

        self.stdout.write(self.style.SUCCESS("smarter.apps.cms.management.commands.initialize_wagtail completed."))
