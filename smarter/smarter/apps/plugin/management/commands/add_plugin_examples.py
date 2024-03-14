# -*- coding: utf-8 -*-
"""Add plugin examples to a user account."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from smarter.apps.account.models import UserProfile
from smarter.apps.plugin.utils import add_example_plugins


User = get_user_model()


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py create_plugin command. This command is used to add plugin examples to a user account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("username", type=str, nargs="?", default=None, help="A user associated with the account.")

    def handle(self, *args, **options):
        """create the plugin."""
        user_profile: UserProfile = None
        username = options["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} does not exist."))
            return

        try:
            user_profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User profile for {user.username} {user.email} does not exist."))
            return

        add_example_plugins(user_profile=user_profile)
