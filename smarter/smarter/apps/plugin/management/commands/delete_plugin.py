"""This module deletes a plugin using manage.py on the command line."""

import sys

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginMeta


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py delete_plugin command. This command is used to delete a plugin."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "-a", "--account_number", type=str, nargs="?", help="Account number that will own the new plugin."
        )
        parser.add_argument("-n", "--name", type=str, nargs="?", help="The name of the plugin to retrieve.")

    def handle(self, *args, **options):
        """delete the plugin."""
        account_number = options["account_number"]
        name = options["name"]

        account: Account = None
        plugin_meta: PluginMeta = None

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Account {account_number} does not exist."))
            sys.exit(1)

        try:
            plugin_meta = PluginMeta.objects.get(name=options["name"], account_id=account.id)
        except PluginMeta.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Plugin {name} does not exist."))
            sys.exit(1)

        controller = PluginController(account=account, plugin_meta=plugin_meta)
        plugin = controller.obj
        plugin.delete()
        self.stdout.write(self.style.SUCCESS(f"Plugin {name} has been deleted."))
