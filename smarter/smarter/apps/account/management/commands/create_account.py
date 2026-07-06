"""
This module provides a Django management command to create a new Account record.

Classes
=======
Command
    Implements logic for the ``manage.py create_account`` command.

Command-line Arguments
=======================
--account_number : str, optional
    The account number for the new account.
--company_name : str, optional
    The company name for the new account.

Functionality
=============
- If ``account_number`` is provided, attempts to find or create an Account with that number and associates the company name.
- If only ``company_name`` is provided, finds or creates the Account based on company name.
- Populates account details like name (in snake_case) and description for newly created accounts.
- Success or failure status is reported to the user.

Usage Example
=============
    python manage.py create_account --account_number=<number> --company_name="<name>"
    python manage.py create_account --company_name="<name>"
"""

from smarter.apps.account.models import Account
from smarter.common.utils import to_snake_case
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Create a new account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The account number for the new account")
        parser.add_argument("--company_name", type=str, help="The company name for the new account", required=False)

    def handle(self, *args, **options):
        """Create the Account."""
        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]

        if account_number:
            account, created = Account.objects.get_or_create(account_number=account_number)
            account.company_name = company_name
            if created:
                account.name = to_snake_case(company_name)
                account.description = f"Account for {company_name}"
            account.save()
        else:
            if not company_name:
                self.handle_completed_failure(msg="company_name must be provided when creating an account.")
                return
            account, created = Account.objects.get_or_create(company_name=company_name)
        if created:
            Account.get_cached_object(invalidate=True, pk=account.pk)  # prime the cache
            self.handle_completed_success(msg=f"Created account: {account.account_number} {account.company_name}")
        else:
            self.handle_completed_success(
                msg=f"Account already exists: {account.account_number} {account.company_name}"
            )
