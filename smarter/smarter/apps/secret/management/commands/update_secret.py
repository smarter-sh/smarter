"""
Django manage.py update_secret command: replace the value of a user's Secret.

Usage::

    python manage.py update_secret --name <secret name> --username <username> [--value <value>]

The Secret must be owned by the user. Without ``--value``, the command prompts for the value, so
that it is not recorded in the shell's history. The value is encrypted before it is saved.
"""

import getpass

from smarter.apps.secret.models import Secret, User, UserProfile
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py update_secret command, which encrypts and saves a new value for a Secret."""

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
            help="The user who owns the Secret.",
        )
        parser.add_argument(
            "--value", type=str, help="The value to encrypt and persist. If not provided, you will be prompted."
        )

    def handle(self, *args, **options):
        """Encrypt the new value, and save it to the Secret."""
        self.handle_begin()

        name = options.get("name")
        if not name:
            self.stdout.write(self.style.ERROR("You must provide a name for the Secret"))
            return
        username = options.get("username")
        if not username:
            self.stdout.write(self.style.ERROR("No username provided. You must provide --username."))
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

        user_profile = UserProfile.get_cached_object(user=user)
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
