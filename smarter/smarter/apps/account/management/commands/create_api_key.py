"""
This module provides a Django management command to create a new API key for a user and account.

Classes
=======
Command
    Implements the logic for the ``manage.py create_api_key`` command.

Command-line Arguments
=======================
--account_number : str, optional
    The Smarter account number to which the user belongs. Format: ####-####-####
--username : str, optional
    The username of the API key owner.
--name : str, optional
    The API key's name, in snake_case. Refused if the owner already has a key with this name.
    Defaults to ``<account_number>.<username>`` in snake_case, suffixed with ``_2``, ``_3``, ...
    when the owner already has a key with that name.
--description : str, optional
    Optional brief text description for the API key.

Functionality
=============
- Finds the specified user and account using the provided arguments.
- Creates a new API key (auth token) for the given user profile, with a name that none of the
  owner's other keys has: a cli command or console page finds a key by its owner and name.
- Outputs the API key value and relevant information. Warns that the key is only shown once.
- Displays instructions for associating the API key with an LLMClient.

Usage Example
=============
    python manage.py create_api_key --account_number=1234-5678-9012 --username=myuser --description="integration key"
"""

from typing import Optional

from django.core.management.base import CommandError

from smarter.apps.account.management.lookups import (
    get_account,
    get_user,
    get_user_profile,
)
from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.common.utils import to_snake_case
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.drf.models import SmarterAuthToken


def api_key_name_exists(user: User, name: str) -> bool:
    """
    Return True if the user already has an API key with this name.

    :param user: The API key's owner.
    :param name: The name, in snake_case, as API key names are stored.
    :returns: True if one of the user's API keys has this name.
    """
    auth_tokens = SmarterAuthToken.objects.filter(user=user, name=name)
    return auth_tokens.exists()


def unused_api_key_name(user: User, base_name: str) -> str:
    """
    Return the base name in snake_case, suffixed with ``_2``, ``_3``, ... if the user already has an API key with it.

    :param user: The API key's owner.
    :param base_name: The preferred name.
    :returns: A name that none of the user's API keys has.
    """
    name = to_snake_case(base_name)
    counter = 1
    while api_key_name_exists(user, name):
        counter += 1
        name = f"{to_snake_case(base_name)}_{counter}"
    return name


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
        parser.add_argument(
            "--name",
            type=str,
            help="Optional name for the api key. Defaults to <account_number>.<username>, with a numeric suffix if taken.",
        )

    def handle(self, *args, **options):
        """Create the api key."""
        self.handle_begin()

        account_number = options["account_number"]
        username = options["username"]
        description = options["description"]
        requested_name = options.get("name")

        if not account_number and not username:
            raise CommandError("Provide an --account_number, a --username, or both.")

        account: Optional[Account] = get_account(account_number=account_number) if account_number else None
        if username:
            user = get_user(username)
            if account:
                user_profile = get_user_profile(f"username {username}", account=account, user=user)
            else:
                first_profile = UserProfile.objects.filter(user=user).first()
                if not first_profile:
                    raise CommandError(f"The user {username} doesn't belong to an account.")
                user_profile = first_profile
            account = user_profile.account
        else:
            # without a username, the account number was given, and get_account() found it.
            if account is None:
                raise CommandError(f"There is no account with the account number {account_number}.")
            user = get_cached_admin_user_for_account(account=account)
            if not user:
                raise CommandError(f"Account {account_number} has no admin user. Add --username to choose the owner.")
            user_profile = get_user_profile(f"username {user.username}", account=account, user=user)

        if requested_name:
            name = to_snake_case(requested_name)
            if api_key_name_exists(user, name):
                raise CommandError(f"The user {user.username} already has an API key named {name}.")
        else:
            name = unused_api_key_name(user, f"{account.account_number}.{user.username}")

        auth_token, token_key = SmarterAuthToken.objects.create(
            user_profile=user_profile,
            name=name,
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
