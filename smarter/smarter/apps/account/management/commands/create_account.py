"""This module is used to create a new account."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account


# pylint: disable=E1101
class Command(BaseCommand):
    """Create a new account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--company_name", type=str, help="The company name for the new account")
        parser.add_argument("--account_number", type=str, help="The account number for the new account")

    def handle(self, *args, **options):
        """create the superuser account."""
        account_number = options["account_number"]
        company_name = options["company_name"]

        if account_number:
            account, created = Account.objects.get_or_create(company_name=company_name, account_number=account_number)
        else:
            account, created = Account.objects.get_or_create(company_name=company_name)
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created account: {account.account_number} {account.company_name}"))
        else:
            self.stdout.write(
                self.style.NOTICE(f"Account already exists: {account.account_number} {account.company_name}")
            )
