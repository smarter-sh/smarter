"""
This module provides a Django management command to create a new API key for a user and account.

Classes
=======
Command
    Implements the logic for the ``manage.py create_api_key`` command.

Command-line Arguments
=====================
--account_number : str, optional
    The Smarter account number to which the user belongs. Format: ####-####-####
--username : str, optional
    The username of the API key owner.
--description : str, optional
    Optional brief text description for the API key.

Functionality
=============
- Finds the specified user and account using the provided arguments.
- Creates a new API key (auth token) for the given user profile.
- Outputs the API key value and relevant information. Warns that the key is only shown once.
- Displays instructions for associating the API key with an LLMClient.

Usage Example
=============
    python manage.py create_api_key --account_number=1234-5678-9012 --username=myuser --description="integration key"
"""

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.drf.models import SmarterAuthToken


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py create_user command.

    This command is used to create a new user for an account.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number",
            type=str,
            help="The Smarter account number to which the user belongs. Format: ####-####-####",
        )
        parser.add_argument("--username", type=str, help="The username of the api key owner")
        parser.add_argument("--description", type=str, help="Optional brief text description for the api key")

    def handle(self, *args, **options):
        """Create the superuser account."""
        self.handle_begin()

        account: Account | None = None
        user: User | None = None
        user_profile: UserProfile | None = None
        account_number = options["account_number"]
        username = options["username"]
        description = options["description"]

        if not account_number and not username:
            self.handle_completed_failure(msg="You must provide an account number or a username")
            return

        if account_number:
            account = Account.objects.get(account_number=account_number)
            user = get_cached_admin_user_for_account(account=account)
        if username:
            user = User.objects.get(username=username)
            user_profile = (
                UserProfile.objects.get(user=user, account=account)
                if account
                else UserProfile.objects.filter(user=user).first()
            )
            if not user_profile:
                self.handle_completed_failure(msg=f"User {username} does not have a user profile")
                return
            account = user_profile.account
        if not user:
            user = (
                User.objects.get(username=username)
                if username
                else get_cached_admin_user_for_account(account=account) if account else None
            )
        user_profile = UserProfile.objects.get(user=user, account=account)

        if not user or not account or not user_profile:
            self.stdout.write(self.style.ERROR("Could not find user or account"))
            return

        auth_token, token_key = SmarterAuthToken.objects.create(
            user_profile=user_profile,
            name=f"{account.account_number}.{user.username}",
            user=user,
            description=description,
        )  # type: ignore[assignment]
        self.handle_completed_success(
            msg=f"Created API key {auth_token.name} for account {account.account_number} and user {user.username}"
        )
        self.stdout.write(self.style.SUCCESS("*" * 80))
        self.stdout.write(self.style.SUCCESS(f"API key: {token_key}"))
        self.stdout.write(self.style.SUCCESS("*" * 80))
        self.stdout.write(
            self.style.WARNING(
                "This API key is only displayed once and cannot be recovered if lost. Store it in a secure location."
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                f"To associate this key with a LLMClient, run `manage.py add_api_key` and pass this key_id: {auth_token.key_id}"
            )
        )
