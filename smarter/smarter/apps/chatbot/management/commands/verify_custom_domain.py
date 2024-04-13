"""This module is used to register a custom domain for a customer account."""

from django.core.management.base import BaseCommand

from smarter.apps.chatbot.models import ChatBotCustomDomain
from smarter.apps.chatbot.tasks import verify_custom_domain
from smarter.common.helpers.aws_helpers import aws_helper


# pylint: disable=E1101
class Command(BaseCommand):
    """This module is used to register a custom domain for a customer account."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("domain", type=str, help="The domain name to register.")

    def handle(self, *args, **options):
        """create the superuser account."""
        domain = options["domain"]

        try:
            custom_domain = ChatBotCustomDomain.objects.get(domain_name=domain)
        except ChatBotCustomDomain.DoesNotExist as e:
            raise ValueError(f"The domain name {domain} is not registered with any Smarter account.") from e

        verify_custom_domain.delay(
            hosted_zone_id=custom_domain.aws_hosted_zone_id, sleep_interval=1800, max_attempts=48
        )
        ns_records = aws_helper.route53.get_ns_records(hosted_zone_id=custom_domain.aws_hosted_zone_id)
        self.stdout.write(
            self.style.SUCCESS(
                f"Smarter has initiated the domain verification process for the domain name {domain} for account {custom_domain.account.account_number} {custom_domain.account.company_name}. This process may take up to 24 hours to complete. Please ensure that the root domain DNS settings include the following NS records: {ns_records}"
            )
        )
