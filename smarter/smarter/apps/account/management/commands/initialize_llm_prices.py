"""Django manage.py initialize_llm_prices command."""

from pydantic import ValidationError

from smarter.apps.account.const import LLM_PRICES_PATH
from smarter.apps.account.llm_price_catalog import (
    load_llm_price_catalog,
    seed_llm_prices,
)
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py initialize_llm_prices command.

    Creates the LLM prices of the price catalog, ``smarter/apps/account/data/llm_prices.yaml``, that
    don't exist yet, so that a new platform's charges have a cost, and its budgets that measure cost
    see them. A price that exists is kept as it is, so an operator's prices survive every
    initialization. ``initialize_platform`` runs it.
    """

    help = "Create the LLM prices of the price catalog that don't exist yet."

    def add_arguments(self, parser):
        """Add the command's arguments."""
        parser.add_argument("--file", type=str, default=LLM_PRICES_PATH, help="The price catalog's file.")

    def handle(self, *args, **options):
        """Create the missing prices."""
        self.handle_begin()
        path = options["file"]
        try:
            catalog = load_llm_price_catalog(path)
        except (ValidationError, ValueError, OSError) as e:
            self.handle_completed_failure(e, f"Failed to read the LLM price catalog {path}.")
            return
        created, kept = seed_llm_prices(catalog)
        self.stdout.write(self.style.SUCCESS(f"Created {created} LLM prices, and kept {kept} that already existed."))
        self.handle_completed_success()
