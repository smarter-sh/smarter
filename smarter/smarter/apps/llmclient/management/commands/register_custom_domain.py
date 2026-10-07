"""This module is used to register a custom domain for a customer account."""

from smarter.apps.account.models import Account
from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.llmclient.models import LLMClientCustomDomain
from smarter.apps.llmclient.tasks import register_custom_domain
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Register a custom domain for a Smarter customer account.

    This management command enables administrators to associate a custom domain name with a specific
    Smarter account. It verifies domain ownership, ensures the domain is not already registered to
    another account, and initiates the registration process in the cloud provider's DNS, e.g. AWS Route 53.

    The command performs the following steps:
    - Accepts the account number and desired domain name as arguments.
    - Checks if the domain name exists and is associated with the correct account.
    - Initiates the registration of the domain using the Smarter platform's domain registration task.
    - Retrieves the name servers of the domain's DNS zone.
    - Outputs instructions for completing DNS verification by updating the root domain's NS records.

    This command is useful for onboarding new customers who require branded llmclient endpoints,
    ensuring proper DNS setup and ownership validation for custom domains.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("account_number", type=str, help="The Smarter account number.")
        parser.add_argument("domain", type=str, help="The domain name to register.")

    def handle(self, *args, **options):
        self.handle_begin()

        if not infrastructure.ready:
            self.handle_completed_failure(msg="Cloud services are currently unavailable. Please try again later.")
            return

        account_number = options["account_number"]
        domain = options["domain"]

        account = Account.objects.get(account_number=account_number)

        try:
            domain_name = LLMClientCustomDomain.objects.get(domain_name=domain)
            if domain_name.user_profile.account != account:
                self.handle_completed_failure(msg=f"The domain name {domain} is already registered by another account.")
                return None
        except LLMClientCustomDomain.DoesNotExist:
            self.handle_completed_failure(msg=f"The domain name {domain} does not exist.")
            return None

        if not register_custom_domain(account_id=account.id, domain_name=domain):
            self.handle_completed_failure(
                msg=f"Failed to register the domain name {domain} for account {account.account_number} {account.company_name}."
            )
            return None

        custom_domain = LLMClientCustomDomain.objects.get(user_profile__account=account, domain_name=domain)
        ns_records = infrastructure.dns.get_name_servers(custom_domain.aws_hosted_zone_id)
        self.handle_completed_success(
            msg=f"Successfully registered the domain name {domain} for account {custom_domain.user_profile.cached_account.account_number} {custom_domain.user_profile.cached_account.company_name}. Please begin the domain verification process once you've added these NS records to the root domain's DNS settings: {ns_records}"
        )
