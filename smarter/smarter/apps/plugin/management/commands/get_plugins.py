# pylint: disable=W0613
"""This module retrieves a list of plugins for an account using manage.py on the command line."""

import sys

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.plugin.utils import Plugins
from smarter.lib.django.user import User, UserType
from smarter.lib.manifest.enum import SAMKeys


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py get_plugins command. This command is used to retrieve a list of plugins for an account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "-a", "--account_number", type=str, required=True, help="Account number that owns the plugins."
        )
        parser.add_argument("-u", "--username", type=str, required=True, help="user that owns the plugins.")

    def handle(self, *args, **options):
        """delete the plugin."""
        account_number = options["account_number"]
        username = options["username"]

        account: Account = None
        user: UserType = None

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"manage.py retrieve_plugin: User {username} does not exist."))
            sys.exit(1)

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"manage.py retrieve_plugin: Account {account_number} does not exist."))
            sys.exit(1)

        try:
            get_cached_user_profile(user=user, account=account)
        except UserProfile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"manage.py retrieve_plugin: UserProfile for {user} and {account} does not exist.")
            )
            sys.exit(1)

        plugins = Plugins(user=user, account=account)
        retval = [
            {"id": plugin[SAMKeys.STATUS.value]["id"], "name": plugin[SAMKeys.METADATA.value]["name"]}
            for plugin in plugins.data
        ]
        print(retval)
