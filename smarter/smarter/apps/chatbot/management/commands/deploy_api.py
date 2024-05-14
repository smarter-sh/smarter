"""This module is used to deploy a customer API."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.common.exceptions import SmarterValueError


# pylint: disable=E1101
class Command(BaseCommand):
    """
    Deploy a customer API. Provide either an account number or a company name.
    Deploys to a URL of the form [user-defined-subdomain].####-####-####.api.smarter.sh/chatbot/
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--name", type=str, help="The name/subdomain for the new API")

    def handle(self, *args, **options):

        account_number = options["account_number"]
        company_name = options["company_name"]
        name = options["name"]

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
            chatbot, _ = ChatBot.objects.get(account=account, name=name)
        except ChatBot.DoesNotExist:
            print(f"Chatbot {name} not found for account {account.account_number} {account.company_name}.")
            return

        if chatbot.deployed:
            print(f"You're all set! {chatbot.hostname} is already deployed.")
            return

        print(f"Deploying {chatbot.hostname}")
        deploy_default_api.delay(chatbot_id=chatbot.id)
