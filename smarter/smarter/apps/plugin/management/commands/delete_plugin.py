"""This module deletes a plugin using manage.py on the command line."""

import sys
from typing import Optional

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.django.user import UserClass as User


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py delete_plugin command. This command is used to delete a plugin."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, required=True, help="Account number that owns the plugin.")
        parser.add_argument("--username", type=str, required=True, help="The user that owns the plugin.")
        parser.add_argument("--name", type=str, required=True, help="The name of the plugin to retrieve.")

    def handle(self, *args, **options):
        """delete the plugin."""
        account_number = options["account_number"]
        username = options["username"]
        name = options["name"]

        account: Optional[Account] = None
        plugin_meta: Optional[PluginMeta] = None
        user: Optional[User] = None
        user_profile: Optional[UserProfile] = None

        try:
            user = User.objects.get(username=username)  # type: ignore
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"manage.py delete_plugin: User {username} does not exist."))
            sys.exit(1)

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"manage.py delete_plugin: Account {account_number} does not exist."))
            sys.exit(1)

        try:
            user_profile = get_cached_user_profile(user=user, account=account)  # type: ignore
        except UserProfile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"manage.py delete_plugin: UserProfile for {user} and {account} does not exist.")
            )
            sys.exit(1)

        self.stdout.write(f"manage.py delete_plugin: Retrieving plugin {name} for account {account}")

        try:
            plugin_meta = PluginMeta.objects.get(name=options["name"], account_id=account.id)  # type: ignore
        except PluginMeta.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Plugin {name} does not exist."))
            sys.exit(1)

        controller = PluginController(account=account, user=user, user_profile=user_profile, plugin_meta=plugin_meta)  # type: ignore
        plugin = controller.obj
        if not plugin:
            self.stdout.write(self.style.ERROR(f"Plugin {name} does not exist."))
            sys.exit(1)
        plugin.delete()
        self.stdout.write(self.style.SUCCESS(f"Plugin {name} has been deleted."))
