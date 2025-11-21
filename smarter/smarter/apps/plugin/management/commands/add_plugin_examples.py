# pylint: disable=W0613
"""Add plugin examples to a user account."""

from typing import Optional

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.utils import add_example_plugins
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Django manage.py create_plugin command. This command is used to add plugin examples to a user account.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--username", type=str, required=True, help="The user that will own the new plugin.")

    def handle(self, *args, **options):
        """create the plugin."""
        self.handle_begin()

        user_profile: Optional[UserProfile] = None
        username = options["username"]

        try:
            user: User = User.objects.get(username=username)
        except User.DoesNotExist as e:
            self.handle_completed_failure(e, f"User {username} does not exist.")
            raise ValueError(f"User {username} does not exist.") from e

        try:
            user_profile = get_cached_user_profile(user=user)  # type: ignore
        except UserProfile.DoesNotExist as e:
            self.handle_completed_failure(e, f"UserProfile for {user} does not exist.")
            raise ValueError(f"UserProfile for {user} does not exist.") from e

        try:
            add_example_plugins(user_profile=user_profile)
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(exc)
            raise

        self.handle_completed_success()
