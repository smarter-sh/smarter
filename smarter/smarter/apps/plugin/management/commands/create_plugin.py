# -*- coding: utf-8 -*-
"""This module is used to manage the superuser account."""
import yaml
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.providers import Plugin


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py create_plugin command. This command is used to create a plugin from a yaml import file."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("plugin_yaml_path", type=str, help="The path to the plugin YAML file")

    def handle(self, *args, **options):
        """create the superuser account."""

        file_path = options["plugin_yaml_path"]
        with open(file_path, "r", encoding="utf-8") as file:
            data = file.read()

        if data:
            try:
                data = yaml.safe_load(data)
            except yaml.YAMLError as exc:
                print("Error in configuration file:", exc)

            user, _ = User.objects.get_or_create(username="admin")
            account, _ = Account.objects.get_or_create(company_name="Smarter")
            user_profile, _ = UserProfile.objects.get_or_create(user=user, account=account)

            data["user"] = user
            data["account"] = account
            data["user_profile"] = user_profile
            data["meta_data"]["author"] = user_profile.id

            plugin = Plugin(data=data)
            print(plugin.to_json())
        else:
            self.stdout.write(self.style.ERROR("Could not open the file."))
