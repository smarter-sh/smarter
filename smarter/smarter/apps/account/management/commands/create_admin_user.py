# -*- coding: utf-8 -*-
"""This module is used to manage the superuser account."""
import secrets
import string

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

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
            self.stdout.write(self.style.SUCCESS(f"Password for user {username} has been changed."))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} does not exist."))

    def handle(self, *args, **options):
        """create the superuser account."""
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if not password:
            password_length = 16
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = "".join(secrets.choice(alphabet) for _ in range(password_length))

        password = make_password(password)

        if username and email:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, email=email, password=password)
            else:
                self.change_password(username, password)
            if not options["password"]:
                print(f"Password: {password}")
        else:
            self.stdout.write(self.style.ERROR("Username and email are required."))

        account, _ = Account.objects.get_or_create(company_name="Smarter")
        UserProfile.objects.get_or_create(user=User.objects.get(username=username), account=account)
