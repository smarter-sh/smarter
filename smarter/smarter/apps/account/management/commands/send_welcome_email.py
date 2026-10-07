"""
Django management command to send a welcome email to an account user.

This module defines the ``send_welcome_email`` management command for the Smarter platform.
It allows administrators to send the HTML welcome email to a user
recorded in the AccountContact table, based on various identifying inputs.

Features
--------
- Sends an HTML welcome email to a target user of an account.
- User can be located via username, email, account number, or company name.
- Will create the AccountContact record if it does not already exist.

Command-line Options
---------------------
- ``--account_number``: The Smarter account number to which the user belongs.
- ``--company_name``: The company name to which the user belongs.
- ``--username``: The username of the user.
- ``--email``: The email address of the user.

Typical Usage
-------------
Used by administrators via ``manage.py send_welcome_email`` to send or re-send
the welcome email to new or existing users for onboarding or support purposes.
"""

from typing import Optional

from smarter.apps.account.models import Account, AccountContact, UserProfile
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Send the html welcome email to a user in the AccountContact table."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--username", type=str, help="The username")
        parser.add_argument("--email", type=str, help="The email address")

    def handle(self, *args, **options):
        """Create the superuser account."""
        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]
        username = options["username"]
        email = options["email"]

        account: Optional[Account] = None

        # the contact's email address: given, or the user's.
        if username:
            user_profile = UserProfile.objects.get(user__username=username)
            account = user_profile.cached_account
            email = email or user_profile.user.email
        elif email and not (account_number or company_name):
            user_profile = UserProfile.objects.get(user__email=email)
            account = user_profile.cached_account

        # an account number or company name chooses the account, e.g. for a contact who isn't a user.
        if account_number or company_name:
            try:
                account = Account.get_cached_object(account_number=account_number, company_name=company_name)
            except Account.DoesNotExist as e:
                self.handle_completed_failure(e, msg=f"Account {account_number or company_name} not found.")
                return

        if not account or not email:
            raise SmarterValueError(
                "You must provide a username, or an email address, and optionally an account number or company name."
            )

        account_contact, created = AccountContact.objects.get_or_create(
            account=account,
            email=email,
        )

        # a new contact is sent the welcome email when it is saved, so it is only re-sent to an existing contact.
        if not created:
            account_contact.send_welcome_email()

        self.handle_completed_success()
