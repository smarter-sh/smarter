"""This module is used to send the html welcome email to a user in the AccountContact table."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, AccountContact, UserProfile
from smarter.common.exceptions import SmarterValueError


# pylint: disable=E1101
class Command(BaseCommand):
    """Send the html welcome email to a user in the AccountContact table."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--username", type=str, help="The username for the new superuser")
        parser.add_argument("--email", type=str, help="The email address for the new superuser")

    def handle(self, *args, **options):
        """create the superuser account."""
        account_number = options["account_number"]
        company_name = options["company_name"]
        username = options["username"]
        email = options["email"]

        account: Account = None

        if username:
            user_profile = UserProfile.objects.get(user__username=username)
            account = user_profile.account
            email = email or user_profile.user.email
        elif email:
            user_profile = UserProfile.objects.get(user__email=email)
            account = user_profile.account
        else:
            if options["account_number"]:
                try:
                    account = Account.objects.get(account_number=account_number)
                except Account.DoesNotExist:
                    print(f"Account {account_number} not found.")
                    return
            elif options["company_name"]:
                try:
                    account = Account.objects.get(company_name=company_name)
                except Account.DoesNotExist:
                    print(f"Account {company_name} not found.")
                    return
            else:
                raise SmarterValueError("You must provide either an account number or a company name.")

            raise SmarterValueError(
                "You must provide either a username or an email address and an account number or company name."
            )

        account_contact, _ = AccountContact.objects.get_or_create(
            account=account,
            email=user_profile.user.email,
        )

        account_contact.send_welcome_email()
