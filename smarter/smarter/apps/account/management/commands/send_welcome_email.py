# -*- coding: utf-8 -*-
"""This module is used to send the html welcome email to a user in the AccountContact table."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import AccountContact, UserProfile


# pylint: disable=E1101
class Command(BaseCommand):
    """Send the html welcome email to a user in the AccountContact table."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--username", type=str, help="The username for the new superuser")
        parser.add_argument("--email", type=str, help="The email address for the new superuser")

    def handle(self, *args, **options):
        """create the superuser account."""
        username = options["username"]
        email = options["email"]

        if username:
            user_profile = UserProfile.objects.get(user__username=username)
        elif email:
            user_profile = UserProfile.objects.get(user__email=email)
        else:
            raise ValueError("You must provide either a username or an email address.")

        account_contact, _ = AccountContact.objects.get_or_create(
            account=user_profile.account,
            email=user_profile.user.email,
        )

        account_contact.send_welcome_email()
