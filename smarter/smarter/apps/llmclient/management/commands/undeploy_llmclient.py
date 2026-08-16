"""This module is used to deploy a customer API."""

from typing import Optional

from smarter.apps.account.models import Account
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.tasks import undeploy_default_api
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Undeploy a customer-facing llmclient API for a Smarter account.

    This management command allows administrators to remove a deployed llmclient from a specific account,
    identified either by account number or company name. The undeployment process deletes the DNS A record
    associated with the llmclient, effectively disabling its public endpoint at
    ``[subdomain].[account-number].api.example.com/llm-client/``.

    **Usage:**
      - Specify the account using either ``--account_number`` or ``--company_name``.
      - Provide the llmclient's name (subdomain) via ``--name``.
      - Optionally use ``--foreground`` to run the undeployment synchronously.

    **Command Workflow:**
      - Retrieve the account by account number or company name.
      - Locate the llmclient by name within the account.
      - Verify that the llmclient is currently deployed and DNS is verified.
      - Initiate undeployment, either synchronously or as a background Celery task.
      - Output progress and completion messages.

    This command is useful for decommissioning llmclients, managing DNS records, and ensuring that
    endpoints are properly removed when llmclients are no longer needed or require redeployment.
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
        llmclient: Optional[LLMClient] = None

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
            llmclient = LLMClient.objects.get(user_profile__account=account, name=name)
        except LLMClient.DoesNotExist as e:
            self.handle_completed_failure(
                e, msg=f"LLMClient {name} not found for account {account.account_number} {account.company_name}."
            )
            return

        if (
            not llmclient.deployed
            and llmclient.dns_verification_status == llmclient.DnsVerificationStatusChoices.NOT_VERIFIED
        ):
            self.handle_completed_failure(msg=f"{llmclient.hostname} is not currently deployed.")
            return

        if foreground:
            self.stdout.write(self.style.NOTICE(f"Deploying {llmclient.hostname}"))
            undeploy_default_api(llmclient_id=llmclient.id)
        else:
            self.stdout.write(self.style.NOTICE(f"Deploying {llmclient.hostname} as a Celery task."))
            undeploy_default_api.delay(llmclient_id=llmclient.id)

        self.handle_completed_success()
