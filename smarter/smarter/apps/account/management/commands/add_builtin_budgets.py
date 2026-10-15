# pylint: disable=W0613
"""
Add the built-in Budgets: one for each Budget example manifest, in data/example-manifests/budgets/.

They are created detached, so they enforce nothing until a superuser attaches them to resources.
A budget that already exists, by name, is left as it is.
"""

import glob
import os

from smarter.apps.account import utils
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py add_builtin_budgets command."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")

    def handle(self, *args, **options):
        """Create the built-in budgets that do not exist yet."""
        self.handle_begin()
        try:
            created = utils.add_builtin_budgets(verbose=options["verbose"])
        # pylint: disable=broad-except
        except Exception as exc:
            # pylint: disable=import-outside-toplevel
            import traceback

            self.handle_completed_failure(exc, f"Stack trace:\n{traceback.format_exc()}")
            raise
        existing = len(glob.glob(os.path.join(utils.BUILTIN_BUDGETS_PATH, "*.yaml"))) - len(created)
        self.stdout.write(
            f"Created {len(created)} built-in budgets: {', '.join(b.name for b in created) or 'none'}. "
            f"{existing} already existed, and were left as they are."
        )
        self.handle_completed_success()
