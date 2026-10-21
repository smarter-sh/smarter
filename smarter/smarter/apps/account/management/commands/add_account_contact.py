"""
This module provides a custom Django management command to add an email address to the Account Contact list associated with an Account in the system.

Classes
=======
Command
    Handles the logic for adding an account contact via command-line arguments.

Command-line Arguments
=======================
--account_number : str, optional
    The Smarter account number to which the user belongs.

--company_name : str, optional
    The company name to which the user belongs.

--email : str, optional
    The email address for the new superuser/account contact.

--username : str, optional
    The username for the new superuser. If provided, the email will be derived
    from the associated user profile.

--language : str, optional
    The language of the welcome email that a new contact is sent, one of
    ``settings.LANGUAGES``, e.g. ``es``. Defaults to the user's preferred language
    (``UserProfile.language``), or English for a contact who isn't a user.

Exceptions
==========
SmarterValueError
    Raised if neither account_number nor company_name is provided, or for
    invalid operation/state.

Usage Example
=============
    python manage.py add_account_contact --account_number=<number> --email=<email>
    python manage.py add_account_contact --company_name="<name>" --username=<username>
    python manage.py add_account_contact --account_number=<number> --email=<email> --language=es
"""

from typing import Optional

from smarter.apps.account.models import (
    Account,
    AccountContact,
    UserProfile,
    welcome_email_languages,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Add an email address to the Account Contact list."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--email", type=str, help="The email address for the new superuser")
        parser.add_argument("--username", type=str, help="The username for the new superuser")
        parser.add_argument(
            "--language",
            type=str,
            choices=welcome_email_languages(),
            help="The language of the welcome email that a new contact is sent. Default: the user's preferred language, or English",
        )

    def handle(self, *args, **options):
        """Create the superuser account."""
        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]
        username = options["username"]
        email = options["email"]
        language = options.get("language")

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

        # a new contact is sent the welcome email, in the given language, when it is saved.
        account_contact = AccountContact.objects.filter(account=account, email=email).first()
        if not account_contact:
            AccountContact(account=account, email=email).save(language=language)
            self.handle_completed_success(
                msg=f"Account Contact {email} added to account {account.account_number} {account.company_name}."
            )

        else:
            self.handle_completed_success(
                msg=f"Account Contact {email} already exists for account {account_contact.account.account_number} {account_contact.account.company_name}."
            )
        return
