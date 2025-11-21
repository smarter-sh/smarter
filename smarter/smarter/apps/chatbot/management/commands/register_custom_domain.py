"""This module is used to register a custom domain for a customer account."""

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBotCustomDomain
from smarter.apps.chatbot.tasks import register_custom_domain
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """This module is used to register a custom domain for a customer account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("account_number", type=str, help="The Smarter account number.")
        parser.add_argument("domain", type=str, help="The domain name to register.")

    def handle(self, *args, **options):
        """register the custom domain."""
        self.handle_begin()

        account_number = options["account_number"]
        domain = options["domain"]

        account = Account.objects.get(account_number=account_number)

        try:
            domain_name = ChatBotCustomDomain.objects.get(domain_name=domain)
            if domain_name.account != account:
                self.handle_completed_failure(msg=f"The domain name {domain} is already registered by another account.")
                return None
        except ChatBotCustomDomain.DoesNotExist:
            self.handle_completed_failure(msg=f"The domain name {domain} does not exist.")
            return None

        if not register_custom_domain(account_id=account.id, domain_name=domain):
            self.handle_completed_failure(
                msg=f"Failed to register the domain name {domain} for account {account.account_number} {account.company_name}."
            )
            return None

        custom_domain = ChatBotCustomDomain.objects.get(account=account, domain_name=domain)
        ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=custom_domain.aws_hosted_zone_id)
        self.handle_completed_success(
            msg=f"Successfully registered the domain name {domain} for account {custom_domain.account.account_number} {custom_domain.account.company_name}. Please begin the domain verification process once you've added these NS records to the root domain's DNS settings: {ns_records}"
        )
