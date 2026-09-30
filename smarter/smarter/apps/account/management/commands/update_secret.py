"""
Django management command to update the encrypted value of a Secret.

This module defines the ``update_secret`` management command for the Smarter platform.
It allows administrators or users to update the encrypted value for a named Secret
associated with a user's profile.

Features
---------
- Updates or sets a new encrypted value for an existing Secret belonging to a user.
- Associates the Secret to the specified user or the current user if not explicitly provided.
- If the value is not passed as an argument, it prompts securely for one at runtime.
- Provides command-line feedback for errors such as missing users, user profiles, or secrets.

Command-line Options
---------------------
- ``--name``: The name of the Smarter Secret to update (required).
- ``--username``: The username associated with the Secret. If not provided, will attempt to use the current user.
- ``--value``: The value to encrypt and store. If not provided, you will be securely prompted for it.

Typical Usage
--------------
Used by administrators or trusted users via ``manage.py update_secret`` to update account secrets,
such as API keys, credentials, or private tokens.
"""

import getpass

from smarter.apps.secret.models import Secret, User, UserProfile
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py create_user command.

    This command is used to update the encrypted value of a Secret.
    """

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
        """Create the superuser account."""
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
