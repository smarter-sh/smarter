"""manage.py create_account command."""

from smarter.apps.account.models import Account
from smarter.common.utils import snake_case
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Create a new account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--company_name", type=str, help="The company name for the new account")
        parser.add_argument("--account_number", type=str, help="The account number for the new account")

    def handle(self, *args, **options):
        """Create the Account."""
        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]

        if account_number:
            account, created = Account.objects.get_or_create(account_number=account_number)
            account.company_name = company_name
            if created:
                account.name = snake_case(company_name)
                account.description = f"Account for {company_name}"
            account.save()
        else:
            account, created = Account.objects.get_or_create(company_name=company_name)
        if created:
            self.handle_completed_success(msg=f"Created account: {account.account_number} {account.company_name}")
        else:
            self.handle_completed_success(
                msg=f"Account already exists: {account.account_number} {account.company_name}"
            )
