"""This module is used to create a new plugin using manage.py"""

import yaml
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import account_admin_user
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.lib.django.user import User, UserType


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py create_plugin command. This command is used to create a plugin from a yaml import file."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "-a", "--account_number", type=str, nargs="?", help="Account number that will own the new plugin."
        )
        parser.add_argument(
            "-u", "--username", type=str, nargs="?", default=None, help="A user associated with the account."
        )
        parser.add_argument("--url", type=str, default=None, help="A public url to a plugin YAML file")
        parser.add_argument(
            "--file_path", type=str, default=None, help="The local file system path to a plugin YAML file"
        )

    def handle(self, *args, **options):
        """create the plugin."""
        account_number = options["account_number"]
        username = options["username"]
        url = options["url"]
        file_path = options["file_path"]

        account: Account = None
        user: UserType = None
        user_profile: UserProfile = None
        data = None

        account = Account.objects.get(account_number=account_number)
        if username:
            user = User.objects.get(username=username)
        else:
            user = account_admin_user(account)
        user_profile = UserProfile.objects.get(user=user, account=account)

        if file_path:
            with open(file_path, encoding="utf-8") as file:
                data = file.read()

            if data:
                try:
                    data = yaml.safe_load(data)
                except yaml.YAMLError as exc:
                    print("Error in configuration file:", exc)
            else:
                self.stdout.write(self.style.ERROR("Could not read the file."))
                return

        if data:
            data["user"] = user
            data["account"] = account
            data["user_profile"] = user_profile
            data["meta_data"]["author"] = user_profile.id

        plugin = PluginStatic(data=data, url=url, user_profile=user_profile)
        print(plugin.to_json())
