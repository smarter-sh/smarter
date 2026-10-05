"""
Django manage.py get_secret command: decrypt and display the value of a named Secret.

Usage::

    python manage.py get_secret --name <secret name> --username <username>

The Secret is looked up by name among those the user may read: their own, and those shared with
them. The decrypted value is printed to stdout, so use the command only where the console output
is private.
"""

from smarter.apps.secret.models import Secret, User, UserProfile
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py get_secret command, which decrypts and displays the value of a Secret."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--name",
            type=str,
            help="The name of the Smarter Secret to retrieve. This is the name of the Secret, not the key.",
        )
        parser.add_argument(
            "--username",
            type=str,
            help="The user who may read the Secret: its owner, or a user it is shared with.",
        )

    def handle(self, *args, **options):
        """Decrypt the Secret and write its value to stdout."""
        self.handle_begin()

        name = options.get("name")
        if not name:
            self.handle_completed_failure(msg="You must provide a name for the Secret")
            return
        username = options.get("username")
        if not username:
            self.handle_completed_failure(msg="No username provided. You must provide --username.")
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.handle_completed_failure(msg=f"User '{username}' does not exist.")
            return

        user_profile = UserProfile.get_cached_object(user=user)
        if not user_profile:
            self.handle_completed_failure(msg=f"User profile for '{username}' does not exist.")
            return

        try:
            secret = Secret.objects.filter(name=name).with_read_permission_for(user).first()
            if not secret:
                raise Secret.DoesNotExist()
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
