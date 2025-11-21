"""This module is used to update the encrypted value of a Secret."""

from smarter.apps.account.models import Secret, User
from smarter.apps.account.utils import get_cached_user_profile
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py get_secret command. This command is used to retrieve the unencrypted value of a Secret."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--name",
            type=str,
            help="The name of the Smarter Secret to update. This is the name of the Secret, not the key.",
        )
        parser.add_argument(
            "--username",
            type=str,
            help="The user to associate with this Secret. If not provided, the current user will be used.",
        )

    def handle(self, *args, **options):
        """create the superuser account."""
        self.handle_begin()

        name = options.get("name")
        if not name:
            self.handle_completed_failure(msg="You must provide a name for the Secret")
            return
        username = options.get("username")
        if not username:
            self.handle_completed_failure(msg="No username provided, using the current user for this Secret.")
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.handle_completed_failure(msg=f"User '{username}' does not exist.")
            return

        user_profile = get_cached_user_profile(user=user)
        if not user_profile:
            self.handle_completed_failure(msg=f"User profile for '{username}' does not exist.")
            return

        try:
            secret = Secret.objects.get(name=name, user_profile=user_profile)
            decrypted_value = secret.get_secret(update_last_accessed=False)
            self.stdout.write(self.style.SUCCESS(f"Secret '{name}' for user '{username}': {decrypted_value}"))
        except Secret.DoesNotExist:
            self.handle_completed_failure(msg=f"Secret '{name}' does not exist for user '{username}'.")
            return
        # pylint: disable=W0718
        except Exception as e:
            self.handle_completed_failure(msg=f"Error retrieving Secret '{name}': {e}")
            return

        self.handle_completed_success()
