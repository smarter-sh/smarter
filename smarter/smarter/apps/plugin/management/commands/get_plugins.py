"""This module retrieves a list of plugins for an account using manage.py on the command line."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.plugin.plugin import Plugins


# pylint: disable=E1101
class Command(BaseCommand):
    """Django manage.py get_plugins command. This command is used to retrieve a list of plugins for an account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("account_number", type=str, help="The account number owning the plugins.")

    def handle(self, *args, **options):
        """delete the plugin."""
        account_number = options["account_number"]

        account: Account = None

        try:
            account = Account.objects.get(account_number=account_number)
        except Account.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Account {account_number} does not exist."))
            return

        plugins = Plugins(account=account)
        retval = [{"id": plugin["id"], "name": plugin["meta_data"]["name"]} for plugin in plugins.data]
        print(retval)
