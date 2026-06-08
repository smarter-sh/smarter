"""This module is used to generate a JSON list of all llm_clients for an account, printed to the console."""

from typing import Optional

from smarter.apps.account.models import Account
from smarter.apps.llm_client.models import LLMClient
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Generate and print a JSON list of all llm_clients for a specified Smarter account.

    This management command retrieves all llm_client instances associated with a given account,
    identified either by account number or company name. It outputs the hostnames of each llm_client
    to the console in JSON format, allowing administrators to quickly view all deployed llm_clients
    for an account.

    **Usage:**
      - Specify the account using ``--account_number`` or ``--company_name``.

    **Command Workflow:**
      - Retrieve the account using the provided identifier.
      - Query all llm_clients linked to the account.
      - Print the hostname of each llm_client to the console.
      - Report completion status.

    This command is useful for auditing, monitoring, or exporting llm_client deployment information
    for a particular account.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")

    def handle(self, *args, **options):
        """Generate a JSON list of all llm_clients for an account."""

        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]

        account: Optional[Account] = None

        if options["account_number"]:
            try:
                account = Account.get_cached_object(account_number=account_number)
            except Account.DoesNotExist:
                self.handle_completed_failure(msg=f"Account {account_number} not found.")
                return
        elif options["company_name"]:
            try:
                account = Account.get_cached_object(company_name=company_name)
            except Account.DoesNotExist:
                self.handle_completed_failure(msg=f"Account {company_name} not found.")
                return
        else:
            raise SmarterValueError("You must provide either an account number or a company name.")

        llm_clients = LLMClient.objects.filter(user_profile__account=account)

        for llm_client in llm_clients:
            print(f"{llm_client.hostname}")

        self.handle_completed_success()
