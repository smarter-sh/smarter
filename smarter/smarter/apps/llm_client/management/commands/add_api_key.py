"""This module is used to add an api key to a llm_client."""

from smarter.apps.account.models import Account
from smarter.apps.llm_client.models import LLMClient, LLMClientAPIKey
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.drf.models import SmarterAuthToken


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Management command for associating an API key with a llm_client.

    This command allows administrators to link an existing API key to a specific llm_client instance
    within a Smarter account. The command requires the account number, the API key ID (UUID format),
    and the llm_client's name (typically its subdomain).

    The command performs the following steps:
      - Retrieves the API key using the provided key ID.
      - Locates the account using the specified account number.
      - Finds the llm_client by its name within the account.
      - Associates the API key with the llm_client, creating the relationship if it does not already exist.
      - Outputs a success message indicating whether the association was newly created or already existed.

    This is useful for managing llm_client authentication and access control in multi-tenant environments.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number",
            type=str,
            help="The Smarter account number to which the user belongs. Format: ####-####-####",
        )
        parser.add_argument("--key_id", type=str, help="an api key id in UUID format")
        parser.add_argument("--name", type=str, help="The name (ie subdomain) of the llm_client")

    def handle(self, *args, **options):
        """Associate an API key with a llm_client based on the provided account number, API key ID, and llm_client name."""
        self.handle_begin()

        account_number = options["account_number"]
        key_id = options["key_id"]
        name = options["name"]

        api_key = SmarterAuthToken.objects.get(key_id=key_id)
        account = Account.objects.get(account_number=account_number)
        llm_client = LLMClient.objects.get(user_profile__account=account, name=name)
        llm_client_api_key, created = LLMClientAPIKey.objects.get_or_create(llm_client=llm_client, api_key=api_key)
        msg = f"API key {key_id} '{llm_client_api_key.api_key.description}'"
        if created:
            self.handle_completed_success(msg + f" has been added to llm_client {name}")
        else:
            self.handle_completed_success(msg + f" is already associated with llm_client {name}")
