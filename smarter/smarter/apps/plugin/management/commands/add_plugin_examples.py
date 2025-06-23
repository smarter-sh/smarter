# pylint: disable=W0613
"""Add plugin examples to a user account."""

from typing import Optional

from django.core.management.base import BaseCommand

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.utils import add_example_plugins
from smarter.lib.django.user import UserClass as User


# pylint: disable=E1101
class Command(BaseCommand):
    """
    Django manage.py create_plugin command. This command is used to add plugin examples to a user account.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--username", type=str, required=True, help="The user that will own the new plugin.")

    def handle(self, *args, **options):
        """create the plugin."""
        user_profile: Optional[UserProfile] = None
        username = options["username"]

        try:
            user: User = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} does not exist."))
            return

        try:
            user_profile = get_cached_user_profile(user=user)  # type: ignore
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User profile for {user.username} {user.email} does not exist."))  # type: ignore
            return

        add_example_plugins(user_profile=user_profile)
