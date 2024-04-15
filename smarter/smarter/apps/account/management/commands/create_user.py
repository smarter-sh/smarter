"""This module is used to manage the superuser account."""

import secrets
import string
from typing import Type

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, SmarterAuthToken, UserProfile


User = get_user_model()
UserType = Type[User]


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py create_user command. This command is used to create a new user for an account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--username", type=str, help="The username for the new superuser")
        parser.add_argument("--email", type=str, help="The email address for the new superuser")
        parser.add_argument("--password", type=str, help="The password for the new superuser")
        parser.add_argument(
            "--admin", action="store_true", default=False, help="True if the new user is an admin, False otherwise."
        )

    def change_password(self, username, new_password):
        """Change the password for a user."""
        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Password for user {username} has been changed to {new_password}."))
            return user
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} does not exist."))
        return None

    def handle(self, *args, **options):
        """create the superuser account."""
        account_number = options["account_number"]
        username = options["username"]
        email = options["email"]
        password = options["password"]
        is_admin = options["admin"]

        account = Account.objects.get(account_number=account_number)

        if not password:
            password_length = 16
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = "".join(secrets.choice(alphabet) for _ in range(password_length))

        if username and email:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, email=email)
                if is_admin:
                    user.is_staff = True
                user.is_active = True
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS("User" + f" {username} {email} has been created."))
                self.stdout.write(self.style.SUCCESS(f"Password: {password}"))
            else:
                user = self.change_password(username, password)
        else:
            self.stdout.write(self.style.ERROR("Username and email are required."))

        UserProfile.objects.get_or_create(user=User.objects.get(username=username), account=account)

        # ensure that the admin user has at least one auth token (api key)
        if SmarterAuthToken.objects.filter(user=user).count() == 0:
            _, token_key = SmarterAuthToken.objects.create(
                account=account, user=user, description="created by manage.py", expiry=None
            )
            self.stdout.write(self.style.SUCCESS(f"created API key: {token_key}"))
