"""This module is used to initialize Wagtail CMS."""

from django.core.management import call_command

from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py initialize_wagtail command. This module is used to initialize Wagtail CMS."""

    help = "Initializes Wagtail."

    def handle(self, *args, **options):
        """Initialize Wagtail CMS."""
        self.handle_begin()

        try:
            call_command("preseed_transfer_table", "wagtailcore.page")
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(exc, msg="Error preseeding transfer table.")
            return

        self.handle_completed_success()
