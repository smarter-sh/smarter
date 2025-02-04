"""This module is used to create a new api key."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.lib.django.user import User
from smarter.lib.drf.models import SmarterAuthToken


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py create_user command. This command is used to create a new user for an account."""

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
        """create the superuser account."""
        account_number = options["account_number"]
        username = options["username"]
        description = options["description"]

        if not account_number and not username:
            self.stdout.write(self.style.ERROR("You must provide an account number or a username"))
            return

        account = None
        if account_number:
            account = Account.objects.get(account_number=account_number)
        if username:
            user = User.objects.get(username=username)
            account = UserProfile.objects.get(user=user).account
        if not user:
            user = User.objects.get(username=username) if username else get_cached_admin_user_for_account(account)
        UserProfile.objects.get(user=user, account=account)

        auth_token, token_key = SmarterAuthToken.objects.create(
            name=f"{account.account_number}.{user.username}", user=user, description=description
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"API key created successfully for account {account.account_number} and user {user.username}"
            )
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
                f"To associate this key with a Chatbot, run `manage.py add_api_key` and pass this key_id: {auth_token.key_id}"
            )
        )
