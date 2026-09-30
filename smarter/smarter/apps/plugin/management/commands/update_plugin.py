# pylint: disable=W0613
"""This module is used to update an existing plugin using manage.py."""

from typing import Optional

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_username,
)
from smarter.apps.plugin.manifest.controller import PLUGIN_MAP, SAM_MAP
from smarter.apps.plugin.models import PluginMeta
from smarter.common.api import SmarterApiVersions
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.loader import SAMLoader, SAMLoaderError


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py update_plugin command.

    This command is used to update a plugin from a yaml import file.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, required=True, help="Account number that owns the plugin.")
        parser.add_argument("--username", type=str, required=True, help="The user that owns the plugin.")
        parser.add_argument("--file_path", type=str, required=True, help="The path to the plugin YAML file")

    def handle(self, *args, **options):
        """Update the plugin."""
        self.handle_begin()

        account_number = options["account_number"]
        username = options["username"]
        file_path = options["file_path"]

        account: Optional[Account] = None
        user: Optional[User] = None
        user_profile: Optional[UserProfile] = None

        try:
            user = get_cached_user_for_username(username=username)
            if user is None:
                raise User.DoesNotExist(f"User with username {username} does not exist.")
        except User.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py update_plugin: User {username} does not exist.",
            )
            raise

        try:
            account = Account.get_cached_object(account_number=account_number)
            if account is None:
                raise Account.DoesNotExist(f"Account with account number {account_number} does not exist.")
        except Account.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py update_plugin: Account {account_number} does not exist.",
            )
            raise

        try:
            user_profile = UserProfile.get_cached_object(user=user, account=account)  # type: ignore
        except UserProfile.DoesNotExist as e:
            self.handle_completed_failure(
                e,
                f"manage.py update_plugin: UserProfile for {user} and {account} does not exist.",
            )
            raise

        try:
            loader = SAMLoader(
                api_version=SmarterApiVersions.V1,
                file_path=file_path,
            )
        except SAMLoaderError as e:
            self.handle_completed_failure(e, f"manage.py update_plugin: {file_path} is not a valid manifest.")
            raise
        if not loader.ready or loader.manifest_kind not in SAM_MAP:
            err = SmarterValueError(f"{file_path} is not a plugin manifest.")
            self.handle_completed_failure(err, "manage.py update_plugin: SAMLoader is not ready.")
            raise err
        manifest = SAM_MAP[loader.manifest_kind](**loader.pydantic_model_dump())
        if not PluginMeta.objects.filter(name=manifest.metadata.name, user_profile=user_profile).exists():
            err = SmarterValueError(f"Plugin {manifest.metadata.name} does not exist for {user_profile}.")
            self.handle_completed_failure(err, f"manage.py update_plugin: {err}")
            raise err

        # a PluginController prefers the stored PluginMeta to the manifest, so
        # the plugin is instantiated from the manifest, which updates it.
        plugin = PLUGIN_MAP[loader.manifest_kind](manifest=manifest, user_profile=user_profile)  # type: ignore[call-arg]

        if plugin and plugin.ready:
            print(plugin.to_json())
        else:
            self.handle_completed_failure(
                None,
                "manage.py update_plugin: Plugin is not ready after update.",
            )
            return
        self.handle_completed_success(msg=f"Plugin {plugin.name} updated successfully.")
