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
- ``--language``: The language of the email, one of ``settings.LANGUAGES``, e.g. ``es``.
  Defaults to the user's preferred language (``UserProfile.language``), or English for a contact
  who isn't a user.

Typical Usage
-------------
Used by administrators via ``manage.py send_welcome_email`` to send or re-send
the welcome email to new or existing users for onboarding or support purposes.
"""

from typing import Optional

from django.core.management.base import CommandError

from smarter.apps.account.management.lookups import get_account
from smarter.apps.account.models import (
    Account,
    AccountContact,
    UserProfile,
    welcome_email_languages,
)
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
        parser.add_argument(
            "--language",
            type=str,
            choices=welcome_email_languages(),
            help="The language of the welcome email. Default: the user's preferred language, or English",
        )

    def get_user_profile(self, description: str, **lookup) -> UserProfile:
        """
        Return the one user profile that matches ``lookup``.

        :param description: how the user was identified, for the error message, e.g. ``username jdoe``.
        :param lookup: the ``UserProfile`` query, e.g. ``user__email="jdoe@example.com"``.
        :returns: the user profile.
        :raises CommandError: if no user profile, or more than one, matches.
        """
        try:
            return UserProfile.objects.get(**lookup)
        except UserProfile.DoesNotExist as e:
            raise CommandError(
                f"There is no user with the {description}. To welcome a contact who isn't a user, "
                "add --account_number or --company_name."
            ) from e
        except UserProfile.MultipleObjectsReturned as e:
            raise CommandError(
                f"The user with the {description} belongs to several accounts. "
                "Add --account_number or --company_name to choose one."
            ) from e

    def handle(self, *args, **options):
        """Send the welcome email."""
        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]
        username = options["username"]
        email = options["email"]
        language = options.get("language")

        account: Optional[Account] = None

        # the contact's email address: given, or the user's.
        if username:
            user_profile = self.get_user_profile(f"username {username}", user__username=username)
            account = user_profile.cached_account
            email = email or user_profile.user.email
        elif email and not (account_number or company_name):
            user_profile = self.get_user_profile(f"email address {email}", user__email=email)
            account = user_profile.cached_account

        # an account number or company name chooses the account, e.g. for a contact who isn't a user.
        if account_number or company_name:
            account = get_account(account_number=account_number, company_name=company_name)

        if not account or not email:
            raise CommandError(
                "Provide a --username, or an --email, and optionally an --account_number or --company_name."
            )

        # a new contact is sent the welcome email when it is saved, so it is only re-sent to an existing contact.
        account_contact = AccountContact.objects.filter(account=account, email=email).first()
        if account_contact:
            account_contact.send_welcome_email(language=language)
        else:
            AccountContact(account=account, email=email).save(language=language)

        self.handle_completed_success()
