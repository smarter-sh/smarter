"""Django manage.py plan_doodles command."""

from smarter.apps.doodle.const import PLANNING_DAYS
from smarter.apps.doodle.editor import edit_days
from smarter.apps.doodle.planner import plan_doodles, planning_window
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py plan_doodles command.

    Plans the doodles of every region, a week ahead, from the calendar. With ``--editor``, it also
    asks the Smarter Doodle Editor about new days, as Celery Beat's task does.
    ``initialize_platform`` runs it, without ``--editor``, after ``load_doodle_themes``.
    """

    help = "Plan the doodles of every region, days ahead."

    def add_arguments(self, parser):
        """Add the command's arguments."""
        parser.add_argument("--days", type=int, default=PLANNING_DAYS, help="How many days ahead to plan.")
        parser.add_argument(
            "--editor",
            action="store_true",
            help="Also ask the Smarter Doodle Editor about new days, a billable LLM prompt for each.",
        )

    def handle(self, *args, **options):
        """Plan the doodles."""
        self.handle_begin()
        days = options["days"]
        planned = plan_doodles(days=days)
        self.stdout.write(self.style.SUCCESS(f"Planned {planned} doodles."))
        if options["editor"]:
            edited = edit_days(planning_window(days=days))
            self.stdout.write(self.style.SUCCESS(f"The Smarter Doodle Editor chose the doodles of {edited} days."))
        self.handle_completed_success()
