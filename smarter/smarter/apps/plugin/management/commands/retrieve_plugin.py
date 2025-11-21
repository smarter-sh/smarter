"""This module retrieves the json representation of a plugin."""

from typing import Optional

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Prints the json representation of a plugin to the console."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, required=True, help="Account number that owns the plugin.")
        parser.add_argument("--username", type=str, required=True, help="The user that owns the plugin.")
        parser.add_argument("--name", type=str, required=True, help="The name of the plugin to retrieve.")

    def handle(self, *args, **options):
        """delete the plugin."""
        self.handle_begin()

        account_number = options["account_number"]
        username = options["username"]
        name = options["name"]

        account: Optional[Account] = None
        plugin_meta: Optional[PluginMeta] = None
        user: Optional[User] = None
        user_profile: Optional[UserProfile] = None

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
            user_profile = get_cached_user_profile(user=user, account=account)  # type: ignore
        except UserProfile.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py retrieve_plugin: UserProfile for {user} and {account} does not exist.",
            )
            raise

        self.stdout.write(f"manage.py retrieve_plugin: Retrieving plugin {name} for account {account}")

        try:
            plugin_meta = PluginMeta.objects.get(name=name, account=account)
        except PluginMeta.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py retrieve_plugin: Plugin {name} does not exist.",
            )
            raise

        controller = PluginController(account=account, user=user, user_profile=user_profile, plugin_meta=plugin_meta)  # type: ignore
        plugin = controller.obj
        if not plugin:
            self.handle_completed_failure(
                None,
                f"Plugin {name} does not exist.",
            )
            raise ValueError(f"Plugin {name} does not exist.")
        print(plugin.data)
        self.handle_completed_success()
