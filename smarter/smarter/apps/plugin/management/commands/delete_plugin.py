"""This module deletes a plugin using manage.py on the command line."""

import sys

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.django.user import User, UserType


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py delete_plugin command. This command is used to delete a plugin."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, nargs="?", help="Account number that owns the plugin.")
        parser.add_argument("--username", type=str, nargs="?", help="The user that owns the plugin.")
        parser.add_argument("--name", type=str, nargs="?", help="The name of the plugin to retrieve.")

    def handle(self, *args, **options):
        """delete the plugin."""
        account_number = options["account_number"]
        username = options["username"]
        name = options["name"]

        account: Account = None
        plugin_meta: PluginMeta = None
        user: UserType = None
        user_profile: UserProfile = None

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
            user_profile = UserProfile.objects.get(user=user, account=account)
        except UserProfile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"manage.py retrieve_plugin: UserProfile for {user} and {account} does not exist.")
            )
            sys.exit(1)

        self.stdout.write(f"manage.py retrieve_plugin: Retrieving plugin {name} for account {account}")

        try:
            plugin_meta = PluginMeta.objects.get(name=options["name"], account_id=account.id)
        except PluginMeta.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Plugin {name} does not exist."))
            sys.exit(1)

        controller = PluginController(account=account, user=user, user_profile=user_profile, plugin_meta=plugin_meta)
        plugin = controller.obj
        plugin.delete()
        self.stdout.write(self.style.SUCCESS(f"Plugin {name} has been deleted."))
