# pylint: disable=W0613
"""
Add the example Budgets: one for each Budget manifest, in data/example-manifests/budgets/ and data/stackademy/.

They are created detached, so they enforce nothing until a superuser attaches them to resources.
A budget that already exists, by name, is left as it is.
"""

from smarter.apps.account import utils
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py add_example_budgets command."""

    help = "Create the example Budgets, detached, in smarter/apps/account/data/example-manifests/budgets and data/stackademy."

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")

    def handle(self, *args, **options):
        """Create the example budgets that do not exist yet."""
        self.handle_begin()
        try:
            created = utils.add_example_budgets(verbose=options["verbose"])
        # pylint: disable=broad-except
        except Exception as exc:
            # pylint: disable=import-outside-toplevel
            import traceback

            self.handle_completed_failure(exc, f"Stack trace:\n{traceback.format_exc()}")
            raise
        existing = len(utils.example_budget_filespecs()) - len(created)
        self.stdout.write(
            f"Created {len(created)} example budgets: {', '.join(b.name for b in created) or 'none'}. "
            f"{existing} already existed, and were left as they are."
        )
        self.handle_completed_success()
