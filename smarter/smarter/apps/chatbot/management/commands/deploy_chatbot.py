"""This module is used to deploy a customer API."""

from typing import Optional

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Deploy a customer API. Provide either an account number or a company name.
    Deploys to a URL of the form [user-defined-subdomain].####-####-####.api.example.com/chatbot/
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--account_number", type=str, help="The Smarter account number to which the user belongs")
        parser.add_argument("--company_name", type=str, help="The company name to which the user belongs")
        parser.add_argument("--name", type=str, help="The name/subdomain for the new ChatBot")
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):
        """
        Deploy a customer-facing chatbot API for a Smarter account.

        This management command enables administrators to deploy a chatbot for a specific account,
        identified either by its account number or company name. The chatbot is deployed to a URL
        structured as ``[subdomain].[account-number].api.example.com/chatbot/``.

        The deployment process checks for the existence of the specified account and chatbot, verifies
        DNS status, and initiates deployment either synchronously (foreground) or asynchronously
        (background Celery task).

        **Usage:**
        - Specify the account using either ``--account_number`` or ``--company_name``.
        - Provide the chatbot's name (subdomain) via ``--name``.
        - Optionally use ``--foreground`` to run the deployment synchronously.

        **Deployment Steps:**
        - Retrieve the account by account number or company name.
        - Locate the chatbot by name within the account.
        - If the chatbot is already deployed and DNS is verified, report success.
        - Otherwise, deploy the chatbot using the appropriate method.
        - Output progress and completion messages.

        This command streamlines the process of making chatbots available to end users, ensuring
        proper DNS verification and deployment status.
        """

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
            chatbot = ChatBot.objects.get(account=account, name=name)
        except ChatBot.DoesNotExist as e:
            self.handle_completed_failure(
                e, msg=f"Chatbot {name} not found for account {account.account_number} {account.company_name}."
            )
            return

        if chatbot.deployed and chatbot.dns_verification_status == ChatBot.DnsVerificationStatusChoices.VERIFIED:
            self.handle_completed_success(msg=f"You're all set! {chatbot.hostname} is already deployed.")
            return

        if foreground:
            self.stdout.write(self.style.NOTICE(f"Deploying {chatbot.hostname}"))
            print()
            deploy_default_api(chatbot_id=chatbot.id)
        else:
            self.stdout.write(self.style.NOTICE(f"Deploying {chatbot.hostname} as a Celery task."))
            deploy_default_api.delay(chatbot_id=chatbot.id)

        self.handle_completed_success(msg=f"Deployment of {chatbot.hostname} has been initiated.")
