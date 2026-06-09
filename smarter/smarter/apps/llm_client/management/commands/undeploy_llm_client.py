"""This module is used to deploy a customer API."""

from typing import Optional

from smarter.apps.account.models import Account
from smarter.apps.llm_client.models import LLMClient
from smarter.apps.llm_client.tasks import undeploy_default_api
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Undeploy a customer-facing llm_client API for a Smarter account.

    This management command allows administrators to remove a deployed llm_client from a specific account,
    identified either by account number or company name. The undeployment process deletes the DNS A record
    associated with the llm_client, effectively disabling its public endpoint at
    ``[subdomain].[account-number].api.example.com/llm-client/``.

    **Usage:**
      - Specify the account using either ``--account_number`` or ``--company_name``.
      - Provide the llm_client's name (subdomain) via ``--name``.
      - Optionally use ``--foreground`` to run the undeployment synchronously.

    **Command Workflow:**
      - Retrieve the account by account number or company name.
      - Locate the llm_client by name within the account.
      - Verify that the llm_client is currently deployed and DNS is verified.
      - Initiate undeployment, either synchronously or as a background Celery task.
      - Output progress and completion messages.

    This command is useful for decommissioning llm_clients, managing DNS records, and ensuring that
    endpoints are properly removed when llm_clients are no longer needed or require redeployment.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--name", type=str, help="The name/subdomain of the LLMClient")
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):
        """Undeploy a customer API."""

        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]
        name = options["name"]
        foreground = options["foreground"]

        account: Optional[Account] = None
        llm_client: Optional[LLMClient] = None

        if options["account_number"]:
            try:
                account = Account.objects.get(account_number=account_number)
            except Account.DoesNotExist:
                print(f"Account {account_number} not found.")
                return
        elif options["company_name"]:
            try:
                account = Account.objects.get(company_name=company_name)
            except Account.DoesNotExist as e:
                self.handle_completed_failure(e, msg=f"Account {company_name} not found.")
                return
        else:
            self.handle_completed_failure(msg="You must provide either an account number or a company name.")
            return

        try:
            llm_client = LLMClient.objects.get(user_profile__account=account, name=name)
        except LLMClient.DoesNotExist as e:
            self.handle_completed_failure(
                e, msg=f"LLMClient {name} not found for account {account.account_number} {account.company_name}."
            )
            return

        if (
            not llm_client.deployed
            and llm_client.dns_verification_status == llm_client.DnsVerificationStatusChoices.NOT_VERIFIED
        ):
            self.handle_completed_failure(msg=f"{llm_client.hostname} is not currently deployed.")
            return

        if foreground:
            self.stdout.write(self.style.NOTICE(f"Deploying {llm_client.hostname}"))
            undeploy_default_api(llm_client_id=llm_client.id)
        else:
            self.stdout.write(self.style.NOTICE(f"Deploying {llm_client.hostname} as a Celery task."))
            undeploy_default_api.delay(llm_client_id=llm_client.id)

        self.handle_completed_success()
