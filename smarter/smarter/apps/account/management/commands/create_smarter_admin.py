# -*- coding: utf-8 -*-
"""This module is used to create a superuser account."""
import secrets
import string
from typing import Type

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, APIKey, UserProfile
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_COMPANY_NAME


User = get_user_model()
UserType = Type[User]


# pylint: disable=E1101
class Command(BaseCommand):
    """Create a new Smarter superuser."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("-u", "--username", type=str, help="The username for the new superuser")
        parser.add_argument("-e", "--email", type=str, help="The email address for the new superuser")
        parser.add_argument("-p", "--password", type=str, help="The password for the new superuser")

    def handle(self, *args, **options):
        """create the superuser account."""
        username = options["username"]
        email = options["email"]
        password = options["password"]

        account, created = Account.objects.get_or_create(
            account_number=SMARTER_ACCOUNT_NUMBER, company_name=SMARTER_COMPANY_NAME
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created account: {account.account_number} {account.company_name}"))

        user, created = User.objects.get_or_create(
            username=username, email=email, is_superuser=True, is_staff=True, is_active=True
        )
        if created:
            if not password:
                password_length = 16
                alphabet = string.ascii_letters + string.digits + string.punctuation
                password = "".join(secrets.choice(alphabet) for _ in range(password_length))

            user.set_password(password)
            user.save()

            self.stdout.write(self.style.SUCCESS(f"Created superuser {username} {email} has been created."))
            self.stdout.write(self.style.SUCCESS(f"Password: {password}"))

        user_profile, created = UserProfile.objects.get_or_create(user=user, account=account)
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created user profile for {user_profile.user.username} {user_profile.user.email}, account {user_profile.account.account_number} {user_profile.account.company_name}"
                )
            )

        # ensure that the Smarter admin user has at least one auth token (api key)
        if APIKey.objects.filter(user=user).count() == 0:
            _, token_key = APIKey.objects.create(user=user, description="created by manage.py", expiry=None)
            self.stdout.write(self.style.SUCCESS(f"created API key: {token_key}"))
