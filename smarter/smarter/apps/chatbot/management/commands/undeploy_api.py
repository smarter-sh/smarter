"""This module is used to deploy a customer API."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.tasks import undeploy_default_api
from smarter.common.exceptions import SmarterValueError


# pylint: disable=E1101
class Command(BaseCommand):
    """
    Undeploy a customer API. Provide either an account number or a company name.
    Undeploys by deleting the DNS A record of the form [user-defined-subdomain].####-####-####.api.smarter.sh/chatbot/
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--name", type=str, help="The name/subdomain for the new API")
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):

        account_number = options["account_number"]
        company_name = options["company_name"]
        name = options["name"]
        foreground = options["foreground"]

        account: Account = None
        chatbot: ChatBot = None

        if options["account_number"]:
            try:
                account = Account.objects.get(account_number=account_number)
            except Account.DoesNotExist:
                print(f"Account {account_number} not found.")
                return
        elif options["company_name"]:
            try:
                account = Account.objects.get(company_name=company_name)
            except Account.DoesNotExist:
                print(f"Account {company_name} not found.")
                return
        else:
            raise SmarterValueError("You must provide either an account number or a company name.")

        try:
            chatbot = ChatBot.objects.get(account=account, name=name)
        except ChatBot.DoesNotExist:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Chatbot {name} not found for account {account.account_number} {account.company_name}."
                )
            )
            return

        if not chatbot.deployed:
            print(f"{chatbot.hostname} is not currently deployed.")
            return

        if foreground:
            self.stdout.write(self.style.NOTICE(f"Deploying {chatbot.hostname}"))
            undeploy_default_api(chatbot_id=chatbot.id)
        else:
            self.stdout.write(self.style.NOTICE(f"Deploying {chatbot.hostname} as a Celery task."))
            undeploy_default_api.delay(chatbot_id=chatbot.id)
