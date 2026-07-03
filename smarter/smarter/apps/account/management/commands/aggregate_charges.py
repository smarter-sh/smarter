"""
This module provides a Django management command to aggregate charges for accounts.

Classes
=======
Command
    Implements the command-line logic for aggregating charges via the ``manage.py aggregate_charges`` command.

Functionality
=============
- Invokes the ``aggregate_charges`` function from ``smarter.apps.account.models.charge`` to aggregate account charge records.
- Provides feedback about the number of aggregated charges via the management command interface.

Usage Example
=============
    python manage.py aggregate_charges
"""

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
