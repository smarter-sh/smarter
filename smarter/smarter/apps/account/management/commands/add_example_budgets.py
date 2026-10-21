"""
Add the example Budgets: one for each Budget manifest, in data/example-manifests/budgets/.

They are created detached, so they enforce nothing until a superuser attaches them to resources.
A budget that already exists, by name, is left as it is.
"""

from typing import Optional

from smarter.apps.account import utils
from smarter.apps.account.models import UserProfile
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """Django manage.py add_example_budgets command."""

    help = "Create the example Budgets, detached, in smarter/apps/account/data/example-manifests/budgets."
    family = "Budget"
    requires_owner = False

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Create the example budgets that do not exist yet."""
        created = utils.add_example_budgets(verbose=self.verbose)
        existing = len(utils.example_budget_filespecs()) - len(created)
        self.stdout.write(
            f"Created {len(created)} example budgets: {', '.join(b.name for b in created) or 'none'}. "
            f"{existing} already existed, and were left as they are."
        )
        return []
