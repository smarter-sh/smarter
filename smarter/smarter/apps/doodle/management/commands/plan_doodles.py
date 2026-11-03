"""Django manage.py plan_doodles command."""

from smarter.apps.doodle.const import PLANNING_DAYS
from smarter.apps.doodle.planner import plan_doodles
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py plan_doodles command.

    Plans the doodles of every region, a week ahead, as Celery Beat's daily task does.
    ``initialize_platform`` runs it, after ``load_doodle_themes``.
    """

    help = "Plan the doodles of every region, days ahead."

    def add_arguments(self, parser):
        """Add the command's arguments."""
        parser.add_argument("--days", type=int, default=PLANNING_DAYS, help="How many days ahead to plan.")

    def handle(self, *args, **options):
        """Plan the doodles."""
        self.handle_begin()
        planned = plan_doodles(days=options["days"])
        self.stdout.write(self.style.SUCCESS(f"Planned {planned} doodles."))
        self.handle_completed_success()
