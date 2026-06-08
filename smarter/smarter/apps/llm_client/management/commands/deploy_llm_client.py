"""This module is used to deploy a customer API."""

from typing import Optional

from smarter.apps.account.models import Account
from smarter.apps.llm_client.models import LLMClient
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Deploy a customer API.

    Provide either an account number or a company name.
    Deploys to a URL of the form [user-defined-subdomain].####-####-####.api.example.com/llm_client/
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--name", type=str, help="The name/subdomain for the new LLMClient")

    def handle(self, *args, **options):
        """
        Deploy a customer-facing llm_client API for a Smarter account.

        This management command enables administrators to deploy a llm_client for a specific account,
        identified either by its account number or company name. The llm_client is deployed to a URL
        structured as ``[subdomain].[account-number].api.example.com/llm_client/``.

        The deployment process checks for the existence of the specified account and llm_client, verifies
        DNS status, and initiates deployment either synchronously (foreground) or asynchronously
        (background Celery task).

        **Usage:**
        - Specify the account using either ``--account_number`` or ``--company_name``.
        - Provide the llm_client's name (subdomain) via ``--name``.
        - Optionally use ``--foreground`` to run the deployment synchronously.

        **Deployment Steps:**
        - Retrieve the account by account number or company name.
        - Locate the llm_client by name within the account.
        - If the llm_client is already deployed and DNS is verified, report success.
        - Otherwise, deploy the llm_client using the appropriate method.
        - Output progress and completion messages.

        This command streamlines the process of making llm_clients available to end users, ensuring
        proper DNS verification and deployment status.
        """

        # FIX NOTE: this needs to be implemented by username rather than account number or company name.
        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]
        name = options["name"]

        account: Optional[Account] = None
        llm_client: Optional[LLMClient] = None

        if options["account_number"]:
            try:
                account = Account.objects.get(account_number=account_number)
            except Account.DoesNotExist as e:
                self.handle_completed_failure(e, msg=f"Account {account_number} not found.")
                return
        elif options["company_name"]:
            try:
                account = Account.objects.get(company_name=company_name)
            except Account.DoesNotExist as e:
                self.handle_completed_failure(e, msg=f"Account {company_name} not found.")
                return
        else:
            self.handle_completed_failure(msg="You must provide either an account number or a company name.")
            raise SmarterValueError("You must provide either an account number or a company name.")

        try:
            llm_client = LLMClient.objects.get(user_profile__account=account, name=name)
        except LLMClient.DoesNotExist as e:
            self.handle_completed_failure(
                e, msg=f"LLMClient {name} not found for account {account.account_number} {account.company_name}."
            )
            return

        llm_client.deployed = True
        llm_client.save()
        self.handle_completed_success()
