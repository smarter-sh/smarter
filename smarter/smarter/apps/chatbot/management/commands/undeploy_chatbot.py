"""This module is used to deploy a customer API."""

from typing import Optional

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.tasks import undeploy_default_api
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Undeploy a customer-facing chatbot API for a Smarter account.

    This management command allows administrators to remove a deployed chatbot from a specific account,
    identified either by account number or company name. The undeployment process deletes the DNS A record
    associated with the chatbot, effectively disabling its public endpoint at
    ``[subdomain].[account-number].api.smarter.sh/chatbot/``.

    **Usage:**
      - Specify the account using either ``--account_number`` or ``--company_name``.
      - Provide the chatbot's name (subdomain) via ``--name``.
      - Optionally use ``--foreground`` to run the undeployment synchronously.

    **Command Workflow:**
      - Retrieve the account by account number or company name.
      - Locate the chatbot by name within the account.
      - Verify that the chatbot is currently deployed and DNS is verified.
      - Initiate undeployment, either synchronously or as a background Celery task.
      - Output progress and completion messages.

    This command is useful for decommissioning chatbots, managing DNS records, and ensuring that
    endpoints are properly removed when chatbots are no longer needed or require redeployment.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--name", type=str, help="The name/subdomain of the ChatBot")
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):
        """Undeploy a customer API."""

        self.handle_begin()

        account_number = options["account_number"]
        company_name = options["company_name"]
        name = options["name"]
        foreground = options["foreground"] if "foreground" in options else False

        account: Optional[Account] = None
        chatbot: Optional[ChatBot] = None

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
            chatbot = ChatBot.objects.get(account=account, name=name)
        except ChatBot.DoesNotExist as e:
            self.handle_completed_failure(
                e, msg=f"Chatbot {name} not found for account {account.account_number} {account.company_name}."
            )
            return

        if (
            not chatbot.deployed
            and chatbot.dns_verification_status == chatbot.DnsVerificationStatusChoices.NOT_VERIFIED
        ):
            self.handle_completed_failure(msg=f"{chatbot.hostname} is not currently deployed.")
            return

        if foreground:
            self.stdout.write(self.style.NOTICE(f"Deploying {chatbot.hostname}"))
            undeploy_default_api(chatbot_id=chatbot.id)
        else:
            self.stdout.write(self.style.NOTICE(f"Deploying {chatbot.hostname} as a Celery task."))
            undeploy_default_api.delay(chatbot_id=chatbot.id)

        self.handle_completed_success()
