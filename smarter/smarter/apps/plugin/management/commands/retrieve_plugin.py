"""This module retrieves the json representation of a plugin."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.static import PluginStatic


# pylint: disable=E1101
class Command(BaseCommand):
    """Prints the json representation of a plugin to the console."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("account_number", type=str, help="The Account ID of the plugin to delete.")
        parser.add_argument("name", type=str, help="The name of the plugin to delete.")

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
            return

        try:
            plugin_meta = PluginMeta.objects.get(name=options["name"], account=account)
        except PluginMeta.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Plugin {name} does not exist."))

        plugin = PluginStatic(plugin_id=plugin_meta.id)
        print(plugin.data)
