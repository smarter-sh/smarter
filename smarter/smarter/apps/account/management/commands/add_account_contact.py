"""This module is used to add an email address to the Account Contact list."""

from typing import Optional

from smarter.apps.account.models import Account, AccountContact, UserProfile
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """add an email address to the Account Contact list."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--email", type=str, help="The email address for the new superuser")
        parser.add_argument("--username", type=str, help="The username for the new superuser")

    def handle(self, *args, **options):
        """create the superuser account."""
        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]
        username = options["username"]
        email = options["email"]

        account: Optional[Account] = None

        if options["account_number"]:
            try:
                account = Account.objects.get(account_number=account_number)
            except Account.DoesNotExist as e:
                self.handle_completed_failure(
                    e,
                    f"Account {account_number} not found.",
                )
                return
        elif options["company_name"]:
            try:
                account = Account.objects.get(company_name=company_name)
            except Account.DoesNotExist as e:
                self.handle_completed_failure(
                    e,
                    f"Account {company_name} not found.",
                )
                return
        else:
            raise SmarterValueError("You must provide either an account number or a company name.")

        if username:
            user_profile = UserProfile.objects.get(user__username=username)
            email = user_profile.user.email

        account_contact, created = AccountContact.objects.get_or_create(
            account=account,
            email=email,
        )

        if created:
            self.handle_completed_success(
                msg=f"Account Contact {email} added to account {account.account_number} {account.company_name}."
            )

        else:
            self.handle_completed_success(
                msg=f"Account Contact {email} already exists for account {account_contact.account.account_number} {account_contact.account.company_name}."
            )
        return
