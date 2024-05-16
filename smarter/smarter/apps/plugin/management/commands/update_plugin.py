# pylint: disable=W0613
"""This module is used to update an existing plugin using manage.py"""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.plugin.model import SAMPlugin
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.loader import SAMLoader


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py create_plugin command. This command is used to create a plugin from a yaml import file."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("account_number", type=str, help="Account number that will own the new plugin.")
        parser.add_argument("plugin_file_path", type=str, help="The path to the plugin YAML file")

    def handle(self, *args, **options):
        """create the plugin."""
        account_number = options["account_number"]
        file_path = options["plugin_file_path"]

        account = Account.objects.get(account_number=account_number)
        loader = SAMLoader(
            api_version=SAMApiVersions.V1.value,
            file_path=file_path,
        )
        manifest = SAMPlugin(
            apiVersion=loader.manifest_api_version,
            kind=loader.manifest_kind,
            metadata=loader.manifest_metadata,
            spec=loader.manifest_spec,
            status=loader.manifest_status,
        )
        controller = PluginController(account=account, manifest=manifest)
        plugin = controller.obj

        if plugin.ready:
            plugin.save()
            print(plugin.to_json())
        else:
            self.stdout.write(self.style.ERROR("Could not open the file."))
