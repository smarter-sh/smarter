# pylint: disable=W0613
"""This module is used to update an existing plugin using manage.py"""

from typing import Optional

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.common.api import SmarterApiVersions
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.loader import SAMLoader


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py update_plugin command. This command is used to update a plugin from a yaml import file."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, required=True, help="Account number that owns the plugin.")
        parser.add_argument("--username", type=str, required=True, help="The user that owns the plugin.")
        parser.add_argument("--file_path", type=str, required=True, help="The path to the plugin YAML file")

    def handle(self, *args, **options):
        """update the plugin."""
        self.handle_begin()

        account_number = options["account_number"]
        username = options["username"]
        file_path = options["file_path"]

        account: Optional[Account] = None
        user: Optional[User] = None
        user_profile: Optional[UserProfile] = None

        try:
            user = User.objects.get(username=username)  # type: ignore
        except User.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py update_plugin: User {username} does not exist.",
            )
            raise

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py update_plugin: Account {account_number} does not exist.",
            )
            raise

        try:
            user_profile = get_cached_user_profile(user=user, account=account)  # type: ignore
        except UserProfile.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py update_plugin: UserProfile for {user} and {account} does not exist.",
            )
            raise

        loader = SAMLoader(
            api_version=SmarterApiVersions.V1,
            file_path=file_path,
        )
        if not loader.ready:
            self.handle_completed_failure(
                None,
                "manage.py update_plugin: SAMLoader is not ready.",
            )
            return
        manifest = SAMStaticPlugin(**loader.pydantic_model_dump())
        controller = PluginController(account=account, user=user, user_profile=user_profile, manifest=manifest)  # type: ignore
        plugin = controller.obj

        if plugin and plugin.ready:
            print(plugin.to_json())
        else:
            self.handle_completed_failure(
                None,
                "manage.py update_plugin: Plugin is not ready after update.",
            )
            return
        self.handle_completed_success(msg=f"Plugin {plugin.name} updated successfully.")
