"""This module is used to update the encrypted value of a Secret."""

import getpass

from smarter.apps.account.models import Secret, User
from smarter.apps.account.utils import get_cached_user_profile
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py create_user command. This command is used to update the encrypted value of a Secret."""

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
        parser.add_argument(
            "--value", type=str, help="The value to encrypt and persist. If not provided, you will be prompted."
        )

    def handle(self, *args, **options):
        """create the superuser account."""
        self.handle_begin()

        name = options.get("name")
        if not name:
            self.stdout.write(self.style.ERROR("You must provide a name for the Secret"))
            return
        username = options.get("username")
        if not username:
            self.stdout.write(self.style.ERROR("No username provided, using the current user for this Secret."))
            return
        value = options.get("value")
        if not value:
            value = getpass.getpass(f"Provide the value for Secret {name} owned by user {username}: ")
        value = Secret.encrypt(value)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as e:
            self.handle_completed_failure(e, msg=f"User '{username}' does not exist.")
            return

        user_profile = get_cached_user_profile(user=user)
        if not user_profile:
            self.handle_completed_failure(msg=f"User profile for '{username}' does not exist.")
            return

        try:
            secret = Secret.objects.get(name=name, user_profile=user_profile)
            secret.encrypted_value = value
            secret.save()
        except Secret.DoesNotExist as e:
            self.handle_completed_failure(e, msg=f"Secret '{name}' does not exist for user '{username}'.")
            return
        # pylint: disable=W0718
        except Exception as e:
            self.handle_completed_failure(e)
            return

        self.handle_completed_success()
