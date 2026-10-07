# pylint: disable=W0613
"""Add builtin MCPClients to an account."""

from typing import Optional

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_username,
    smarter_cached_objects,
)
from smarter.apps.mcpclient.utils import add_builtin_mcpclients
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py add_builtin_mcpclients command."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--username",
            type=str,
            help="The user that will own the new MCPClients.",
            default=smarter_cached_objects.smarter_admin.username,
        )
        parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")

    def handle(self, *args, **options):
        """Create the MCPClients."""
        self.handle_begin()

        user_profile: Optional[UserProfile] = None
        username = options["username"]
        verbose = options["verbose"]

        try:
            user: Optional[User] = get_cached_user_for_username(username=username)
            if user is None:
                raise User.DoesNotExist(f"User with username {username} does not exist.")
        except User.DoesNotExist as e:
            self.handle_completed_failure(e, f"User {username} does not exist.")
            raise ValueError(f"User {username} does not exist.") from e

        try:
            user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
        except UserProfile.DoesNotExist as e:
            self.handle_completed_failure(e, f"UserProfile for {user} does not exist.")
            raise ValueError(f"UserProfile for {user} does not exist.") from e

        try:
            success = add_builtin_mcpclients(user_profile=user_profile, verbose=verbose)
        # pylint: disable=broad-except
        except Exception as exc:
            # pylint: disable=import-outside-toplevel
            import traceback

            tb = traceback.format_exc()
            self.handle_completed_failure(exc, f"Stack trace:\n{tb}")
            raise

        if not success:
            self.stdout.write(self.style.WARNING("One or more built-in MCPClient manifests failed to apply."))
        self.handle_completed_success()
