"""This module is used to add an api key to a chatbot."""

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.drf.models import SmarterAuthToken


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Management command for associating an API key with a chatbot.

    This command allows administrators to link an existing API key to a specific chatbot instance
    within a Smarter account. The command requires the account number, the API key ID (UUID format),
    and the chatbot's name (typically its subdomain).

    The command performs the following steps:
      - Retrieves the API key using the provided key ID.
      - Locates the account using the specified account number.
      - Finds the chatbot by its name within the account.
      - Associates the API key with the chatbot, creating the relationship if it does not already exist.
      - Outputs a success message indicating whether the association was newly created or already existed.

    This is useful for managing chatbot authentication and access control in multi-tenant environments.
    """

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
        self.handle_begin()

        account_number = options["account_number"]
        key_id = options["key_id"]
        name = options["name"]

        api_key = SmarterAuthToken.objects.get(key_id=key_id)
        account = Account.objects.get(account_number=account_number)
        chatbot = ChatBot.objects.get(account=account, name=name)
        chatbot_api_key, created = ChatBotAPIKey.objects.get_or_create(chatbot=chatbot, api_key=api_key)
        msg = f"API key {key_id} '{chatbot_api_key.api_key.description}'"
        if created:
            self.handle_completed_success(msg + f" has been added to chatbot {name}")
        else:
            self.handle_completed_success(msg + f" is already associated with chatbot {name}")
