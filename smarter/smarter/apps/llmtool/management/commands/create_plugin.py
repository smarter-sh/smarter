# pylint: disable=W0613,R0914
"""This module is used to create a new plugin using manage.py."""

from typing import Optional

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_username,
)
from smarter.apps.llmtool.manifest.controller import SAM_MAP, PluginController
from smarter.apps.llmtool.plugin.base import PluginBase
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.parsing import read_manifest_file


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py create_plugin command.

    This command is used to create a plugin from a yaml import file.
    """

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
        """Create the plugin."""
        self.handle_begin()
        account_number: Optional[str] = options["account_number"]
        file_path: Optional[str] = options["file_path"]
        username: Optional[str] = options["username"]

        account: Optional[Account]
        user: Optional[User]

        self.stdout.write(f"manage.py create_plugin: account_number: {account_number} file_path: {file_path}")

        if username:
            try:
                user = get_cached_user_for_username(username=username)
                if user is None:
                    raise User.DoesNotExist(f"User with username {username} does not exist.")
            except User.DoesNotExist as e:
                self.handle_completed_failure(e, f"User {username} does not exist.")

        try:
            account = Account.get_cached_object(invalidate=False, account_number=account_number)  # type: ignore[assignment]
            if account is None:
                raise Account.DoesNotExist(f"Account with account number {account_number} does not exist.")
        except Account.DoesNotExist as e:
            self.handle_completed_failure(e, f"Account {account_number} does not exist.")

        try:
            user_profile = UserProfile.get_cached_object(user=user, account=account)  # type: ignore
        except UserProfile.DoesNotExist as e:
            self.handle_completed_failure(e, f"UserProfile for {user} and {account} does not exist.")

        try:
            data = read_manifest_file(str(file_path))
        except SAMValidationError as e:
            self.handle_completed_failure(e, f"manage.py create_plugin. {file_path} is not a valid manifest.")
            raise

        kind = data.get("kind")
        if kind not in SAM_MAP:
            err = SmarterValueError(f"{file_path} is not a plugin manifest.")
            self.handle_completed_failure(err, f"manage.py create_plugin. {file_path} is not a plugin manifest.")
            raise err

        plugin_class = SAM_MAP[kind]
        manifest = plugin_class.model_validate(data)
        self.stdout.write(f"Creating {plugin_class.__name__} {manifest.metadata.name} for account {account}...")
        controller = PluginController(user_profile=user_profile, manifest=manifest)  # type: ignore
        plugin = controller.obj

        if isinstance(plugin, PluginBase) and plugin.ready:
            self.handle_completed_success(msg=f"Plugin {plugin.name} created successfully.")
        else:
            self.handle_completed_failure(None, "Encountered an error while attempting to create the plugin.")
