# pylint: disable=W0613
"""This module is used to create a new plugin using manage.py"""

import sys
from typing import Optional

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.common.api import SmarterApiVersions
from smarter.lib.django.user import UserClass
from smarter.lib.manifest.loader import SAMLoader


# pylint: disable=E1101
class Command(BaseCommand):
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
        account_number: Optional[str] = options["account_number"]
        file_path: Optional[str] = options["file_path"]
        username: Optional[str] = options["username"]

        account: Account
        user: UserClass

        self.stdout.write(f"manage.py create_plugin: account_number: {account_number} file_path: {file_path}")

        try:
            user = UserClass.objects.get(username=username)  # type: ignore
        except UserClass.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"manage.py create_plugin: User {username} does not exist."))
            sys.exit(1)

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"manage.py create_plugin: Account {account_number} does not exist."))
            sys.exit(1)

        try:
            user_profile = get_cached_user_profile(user=user, account=account)  # type: ignore
        except UserProfile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"manage.py create_plugin: UserProfile for {user} and {account} does not exist.")
            )
            sys.exit(1)

        loader = SAMLoader(
            api_version=SmarterApiVersions.V1,
            file_path=file_path,
        )
        if not loader.ready:
            self.stdout.write(self.style.ERROR("manage.py create_plugin. SAMLoader is not ready."))
            sys.exit(1)
        manifest = SAMStaticPlugin(**loader.pydantic_model_dump())

        self.stdout.write(f"Creating plugin {manifest.metadata.name} for account {account}...")
        controller = PluginController(account=account, user=user, user_profile=user_profile, manifest=manifest)  # type: ignore
        plugin = controller.obj

        if isinstance(plugin, PluginBase) and plugin.ready:
            self.stdout.write(self.style.SUCCESS(f"Plugin {plugin.name} for account {account} created successfully."))
        else:
            self.stdout.write(self.style.ERROR("Encountered an error while attempting to create the plugin."))
