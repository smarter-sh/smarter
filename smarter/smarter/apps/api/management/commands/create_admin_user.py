# -*- coding: utf-8 -*-
"""This module is used to manage the superuser account."""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


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
        if username and email and password:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, email=email, password=password)
            else:
                self.change_password(username, password)
        else:
            self.stdout.write(self.style.ERROR("Username, email, and password are required."))
