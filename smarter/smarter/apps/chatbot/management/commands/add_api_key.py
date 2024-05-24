"""This module is used to add an api key to a chatbot."""

from django.core.management.base import BaseCommand

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey
from smarter.lib.drf.models import SmarterAuthToken


# pylint: disable=E1101
class Command(BaseCommand):
    """Add an api key to a chatbot."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number",
            type=str,
            help="The Smarter account number to which the user belongs. Format: ####-####-####",
        )
        parser.add_argument("--key_id", type=str, help="an api key id in UUID format")
        parser.add_argument("--name", type=str, help="The name (ie subdomain) of the chatbot")

    def handle(self, *args, **options):
        """create the superuser account."""
        account_number = options["account_number"]
        key_id = options["key_id"]
        name = options["name"]

        api_key = SmarterAuthToken.objects.get(key_id=key_id)
        account = Account.objects.get(account_number=account_number)
        chatbot = ChatBot.objects.get(account=account, name=name)
        chatbot_api_key, created = ChatBotAPIKey.objects.get_or_create(chatbot=chatbot, api_key=api_key)
        msg = f"API key {key_id} '{chatbot_api_key.api_key.description}'"
        if created:
            self.stdout.write(self.style.SUCCESS(msg + f" has been added to chatbot {name}"))
        else:
            self.stdout.write(self.style.NOTICE(msg + f" is already associated with chatbot {name}"))
