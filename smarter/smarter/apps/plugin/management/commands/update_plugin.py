# -*- coding: utf-8 -*-
"""This module is used to update an existing plugin using manage.py"""
import yaml
from django.core.management.base import BaseCommand

from smarter.apps.account.models import UserProfile

from ...plugin import Plugin


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py create_plugin command. This command is used to create a plugin from a yaml import file."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("plugin_file_path", type=str, help="The path to the plugin YAML file")

    def handle(self, *args, **options):
        """create the plugin."""
        user_profile: UserProfile = None

        file_path = options["plugin_file_path"]
        with open(file_path, "r", encoding="utf-8") as file:
            data = file.read()

        if data:
            try:
                data = yaml.safe_load(data)
            except yaml.YAMLError as exc:
                print("Error in configuration file:", exc)

            user_profile = data["meta_data"]["author"]
            data["user_profile"] = user_profile
            data["user"] = user_profile.user
            data["account"] = user_profile.account

            plugin = Plugin(data=data)
            if plugin.ready:
                print(plugin.to_json())
        else:
            self.stdout.write(self.style.ERROR("Could not open the file."))
