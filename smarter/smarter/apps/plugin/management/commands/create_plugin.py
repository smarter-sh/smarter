# pylint: disable=W0613
"""This module is used to create a new plugin using manage.py"""

from typing import Optional

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.manifest.controller import SAM_MAP, PluginController
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.common.api import SmarterApiVersions
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.loader import SAMLoader


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py create_plugin command. This command is used to create a plugin from a yaml import file."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number", type=str, required=True, help="Account number that will own the new plugin."
        )
        parser.add_argument("--username", type=str, required=True, help="The user that will own the new plugin.")
        parser.add_argument(
            "--file_path", type=str, required=True, help="The local file system path to a plugin YAML file"
        )

    def handle(self, *args, **options):
        """create the plugin."""
        self.handle_begin()
        account_number: Optional[str] = options["account_number"]
        file_path: Optional[str] = options["file_path"]
        username: Optional[str] = options["username"]

        account: Account
        user: User

        self.stdout.write(f"manage.py create_plugin: account_number: {account_number} file_path: {file_path}")

        try:
            user = User.objects.get(username=username)  # type: ignore
        except User.DoesNotExist as e:
            self.handle_completed_failure(e, f"User {username} does not exist.")

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist as e:
            self.handle_completed_failure(e, f"Account {account_number} does not exist.")

        try:
            user_profile = get_cached_user_profile(user=user, account=account)  # type: ignore
        except UserProfile.DoesNotExist as e:
            self.handle_completed_failure(e, f"UserProfile for {user} and {account} does not exist.")

        loader = SAMLoader(
            api_version=SmarterApiVersions.V1,
            file_path=file_path,
        )

        if not loader.ready:
            self.handle_completed_failure(None, "manage.py create_plugin. SAMLoader is not ready.")

        plugin_class = SAM_MAP[loader.manifest_kind]
        manifest = plugin_class(**loader.pydantic_model_dump())
        self.stdout.write(f"Creating {plugin_class.__name__} {manifest.metadata.name} for account {account}...")
        controller = PluginController(account=account, user=user, user_profile=user_profile, manifest=manifest)  # type: ignore
        plugin = controller.obj

        if isinstance(plugin, PluginBase) and plugin.ready:
            self.handle_completed_success(msg=f"Plugin {plugin.name} created successfully.")
        else:
            self.handle_completed_failure(None, "Encountered an error while attempting to create the plugin.")
