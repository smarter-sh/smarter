"""
This module provides a Django management command to remove an email address from the Account Contact list associated with a specific Account.

Classes
=======
Command
    Implements the logic for the ``manage.py delete_account_contact`` command.

Command-line Arguments
=======================
--account_number : str, optional
    The Smarter account number from which the contact should be removed.
--company_name : str, optional
    The company name from which the contact should be removed.
--email : str, optional
    The email address of the contact to be removed.
--username : str, optional
    The username for identifying the account contact. If supplied, the email is looked up from this username.

Functionality
=============
- Resolves the account from account number or company name.
- Optional user's username can be supplied to look up the email address.
- Deletes the contact with the specified email from the resolved account.
- Handles errors for missing accounts or contacts appropriately.

Usage Example
=============
    python manage.py delete_account_contact --account_number=<number> --email=<email>
    python manage.py delete_account_contact --company_name="<name>" --username=<username>
"""

from django.core.management.base import CommandError

from smarter.apps.account.management.lookups import get_account, get_user
from smarter.apps.account.models import AccountContact
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Remove an email address from the Account Contact list."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--email", type=str, help="The email address for the new superuser")
        parser.add_argument("--username", type=str, help="The username for the new superuser")

    def handle(self, *args, **options):
        """Remove the contact from the account."""
        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]
        username = options["username"]
        email = options["email"]

        account = get_account(account_number=account_number, company_name=company_name)
        if username:
            email = get_user(username).email
        if not email:
            raise CommandError("Provide an --email, or the --username of a user.")

        account_contact = AccountContact.objects.filter(account=account, email=email).first()
        if not account_contact:
            raise CommandError(f"{email} is not a contact of account {account.account_number} {account.company_name}.")

        account_contact.delete()
        self.handle_completed_success(
            msg=f"Account Contact {email} removed from account {account_contact.account.account_number} {account_contact.account.company_name}."
        )
