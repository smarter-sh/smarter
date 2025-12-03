"""This module is used to register a custom domain for a customer account."""

from smarter.apps.chatbot.models import ChatBotCustomDomain
from smarter.apps.chatbot.tasks import verify_custom_domain
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Verify a custom domain for a Smarter customer account.

    This management command initiates and monitors the DNS verification process for a custom domain
    associated with a Smarter account. It checks that the domain is registered, triggers verification
    using AWS Route 53, and provides instructions for updating DNS records.

    The command performs the following steps:

    - Accepts the domain name as an argument, with an option to run verification in the foreground.
    - Checks that the domain is registered to a Smarter account.
    - Initiates the verification process, either synchronously or as a background Celery task.
    - Retrieves the AWS Route 53 NS records for the domain's hosted zone.
    - Outputs instructions for completing DNS verification, including required NS records.

    This command is useful for administrators onboarding new customers or updating domain settings,
    ensuring that custom domains are properly verified and ready for use with Smarter chatbots.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("domain", type=str, help="The domain name to register.")
        parser.add_argument("--foreground", action="store_true", help="Run the task in the foreground")

    def handle(self, *args, **options):
        """create the superuser account."""
        self.handle_begin()

        domain = options["domain"]
        foreground = options["foreground"] if "foreground" in options else False

        try:
            custom_domain = ChatBotCustomDomain.objects.get(domain_name=domain)
        except ChatBotCustomDomain.DoesNotExist as e:
            self.handle_completed_failure(
                e, msg=f"The domain name {domain} is not registered with any Smarter account."
            )
            return

        if foreground:
            print(f"Verifying {domain}")
            verify_custom_domain(hosted_zone_id=custom_domain.aws_hosted_zone_id, sleep_interval=1800, max_attempts=48)
            ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=custom_domain.aws_hosted_zone_id)
            self.handle_completed_success(
                msg=f"Successfully verified the domain name {domain} for account {custom_domain.account.account_number} {custom_domain.account.company_name}."
            )
        else:
            print(f"Verifying {domain} as a Celery task.")
            verify_custom_domain.delay(
                hosted_zone_id=custom_domain.aws_hosted_zone_id, sleep_interval=1800, max_attempts=48
            )
            ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=custom_domain.aws_hosted_zone_id)

            self.handle_completed_success(
                msg=f"Smarter has initiated the domain verification process for the domain name {domain} for account {custom_domain.account.account_number} {custom_domain.account.company_name}. This process may take up to 24 hours to complete. Please ensure that the root domain DNS settings include the following NS records: {ns_records}"
            )
