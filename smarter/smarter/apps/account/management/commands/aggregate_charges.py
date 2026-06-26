"""Manage.py aggregate_charges command."""

from smarter.apps.account.models.charge import aggregate_charges
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Aggregate charges."""

    def handle(self, *args, **options):
        """Aggregate the charges."""
        self.handle_begin()

        num_aggregated = aggregate_charges()
        self.handle_completed_success(msg=f"Aggregated {num_aggregated} charges.")
