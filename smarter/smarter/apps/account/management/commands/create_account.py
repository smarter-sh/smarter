"""This module is used to create a new account."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account


# pylint: disable=E1101
class Command(BaseCommand):
    """Create a new account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--company_name", type=str, help="The company name for the new account")

    def handle(self, *args, **options):
        """create the superuser account."""
        company_name = options["company_name"]

        account = Account.objects.create(company_name=company_name)
        print(f"Created account: {account.account_number} {account.company_name}")
