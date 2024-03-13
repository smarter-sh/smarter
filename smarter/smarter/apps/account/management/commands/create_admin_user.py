# -*- coding: utf-8 -*-
"""This module is used to manage the superuser account."""
import secrets
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from knox.models import AuthToken

from smarter.apps.account.models import Account, UserProfile


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py create_admin_user command. This command is used to create a new superuser account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--username", type=str, help="The username for the new superuser")
        parser.add_argument("--email", type=str, help="The email address for the new superuser")
        parser.add_argument("--password", type=str, help="The password for the new superuser")

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
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if not password:
            password_length = 16
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = "".join(secrets.choice(alphabet) for _ in range(password_length))

        if username and email:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, email=email)
                user.is_superuser = False
                user.is_staff = True
                user.is_active = True
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Creating admin account: {username} {email}"))
                self.stdout.write(self.style.SUCCESS(f"Password: {password}"))
            else:
                user = self.change_password(username, password)
        else:
            self.stdout.write(self.style.ERROR("Username and email are required."))

        account, _ = Account.objects.get_or_create(company_name="Smarter")
        UserProfile.objects.get_or_create(user=User.objects.get(username=username), account=account)

        # ensure that the admin user has at least one auth token (api key)
        if AuthToken.objects.filter(user=user).count() == 0:
            _, token_key = AuthToken.objects.create(user=user)
            self.stdout.write(self.style.SUCCESS(f"created API key: {token_key}"))
