# pylint: disable=W0613
"""This module retrieves a list of plugins for an account using manage.py on the command line."""

from typing import Optional

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.plugin.utils import Plugins
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.enum import SAMKeys


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py get_plugins command. This command is used to retrieve a list of plugins for an account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "-a", "--account_number", type=str, required=True, help="Account number that owns the plugins."
        )
        parser.add_argument("-u", "--username", type=str, required=True, help="user that owns the plugins.")

    def handle(self, *args, **options):
        """delete the plugin."""
        self.handle_begin()

        account_number = options["account_number"]
        username = options["username"]

        account: Optional[Account] = None
        user: Optional[User] = None

        try:
            user = User.objects.get(username=username)  # type: ignore
        except User.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py retrieve_plugin: User {username} does not exist.",
            )
            raise

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py retrieve_plugin: Account {account_number} does not exist.",
            )
            raise

        try:
            get_cached_user_profile(user=user, account=account)  # type: ignore
        except UserProfile.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py retrieve_plugin: UserProfile for {user} and {account} does not exist.",
            )
            raise

        plugins = Plugins(user=user, account=account)  # type: ignore
        retval = [
            {"id": plugin[SAMKeys.STATUS.value]["id"], "name": plugin[SAMKeys.METADATA.value]["name"]}
            for plugin in plugins.data
        ]
        print(retval)
        self.handle_completed_success()
