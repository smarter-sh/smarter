# -*- coding: utf-8 -*-
"""This module is used to create a new plugin using manage.py"""
import yaml
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile

from ...plugin import Plugin


User = get_user_model()


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py create_plugin command. This command is used to create a plugin from a yaml import file."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "account_number", type=str, nargs="?", default=None, help="Account number that will own the new plugin."
        )
        parser.add_argument("username", type=str, nargs="?", default=None, help="A user associated with the account.")
        parser.add_argument("plugin_yaml_path", type=str, help="The path to the plugin YAML file")

    def handle(self, *args, **options):
        """create the plugin."""
        account: Account = None
        user: User = None
        user_profile: UserProfile = None
        account_number = options["account_number"]
        username = options["username"]

        file_path = options["plugin_yaml_path"]
        with open(file_path, "r", encoding="utf-8") as file:
            data = file.read()

        if data:
            try:
                data = yaml.safe_load(data)
            except yaml.YAMLError as exc:
                print("Error in configuration file:", exc)

            try:
                if account_number:
                    account = Account.objects.get(account_number=account_number)
                else:
                    account, _ = Account.objects.get_or_create(company_name="Smarter")
            except Account.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Account {account_number} does not exist."))
                return

            try:
                if username:
                    user = User.objects.get(username=username)
                else:
                    user, _ = User.objects.get_or_create(username="admin")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User {username} does not exist."))
                return

            try:
                user_profile, _ = UserProfile.objects.get_or_create(user=user, account=account)
            except UserProfile.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"User profile for {user.username} {user.email} does not exist for account {account.account_number}."
                    )
                )
                return

            data["user"] = user
            data["account"] = account
            data["user_profile"] = user_profile
            data["meta_data"]["author"] = user_profile.id

            plugin = Plugin(data=data)
            print(plugin.to_json())
        else:
            self.stdout.write(self.style.ERROR("Could not open the file."))
