# pylint: disable=W0613
"""This module is used to update an existing plugin using manage.py"""

import sys
from typing import Optional

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.common.api import SmarterApiVersions
from smarter.lib.django.user import UserClass as User
from smarter.lib.manifest.loader import SAMLoader


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py update_plugin command. This command is used to update a plugin from a yaml import file."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, required=True, help="Account number that owns the plugin.")
        parser.add_argument("--username", type=str, required=True, help="The user that owns the plugin.")
        parser.add_argument("--file_path", type=str, required=True, help="The path to the plugin YAML file")

    def handle(self, *args, **options):
        """update the plugin."""
        account_number = options["account_number"]
        username = options["username"]
        file_path = options["file_path"]

        account: Optional[Account] = None
        user: Optional[User] = None
        user_profile: Optional[UserProfile] = None

        try:
            user = User.objects.get(username=username)  # type: ignore
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"manage.py retrieve_plugin: User {username} does not exist."))
            sys.exit(1)

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"manage.py retrieve_plugin: Account {account_number} does not exist."))
            sys.exit(1)

        try:
            user_profile = get_cached_user_profile(user=user, account=account)  # type: ignore
        except UserProfile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"manage.py retrieve_plugin: UserProfile for {user} and {account} does not exist.")
            )
            sys.exit(1)

        loader = SAMLoader(
            api_version=SmarterApiVersions.V1,
            file_path=file_path,
        )
        if not loader.ready:
            self.stdout.write(self.style.ERROR("manage.py update_plugin: SAMLoader is not ready."))
            return
        manifest = SAMStaticPlugin(**loader.pydantic_model_dump())
        controller = PluginController(account=account, user=user, user_profile=user_profile, manifest=manifest)  # type: ignore
        plugin = controller.obj

        if plugin and plugin.ready:
            print(plugin.to_json())
        else:
            self.stdout.write(self.style.ERROR("Could not open the file."))
