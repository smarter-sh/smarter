# pylint: disable=W0613
"""utility for running api/v1 cli endpoints to verify that they work."""

from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import Account
from smarter.apps.account.utils import account_admin_user
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments


# pylint: disable=E1101
class Command(BaseCommand):
    """utility for running api/v1 cli endpoints to verify that they work."""

    account = Account.get_account_by_number(SMARTER_ACCOUNT_NUMBER)
    user = account_admin_user(account=account)

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "username", type=str, nargs="?", default="admin", help="A user associated with the account."
        )

    def handle(self, *args, **options):

        print("*" * 80)
        print("Running API CLI endpoint verifications.")
        print("Environment: ", smarter_settings.environment)
        print("Account: ", SMARTER_ACCOUNT_NUMBER)
        print("User: ", self.user.username)
        print("*" * 80)

        def get_response(path):
            client = Client()
            client.force_login(self.user)

            if smarter_settings.environment != SmarterEnvironments.LOCAL:
                response = client.post(path=path, HTTP_HOST=smarter_settings.environment_domain)
                url = f"https://{smarter_settings.environment_domain}{path}"
            else:
                response = client.post(path=path)
                url = f"http://localhost:8000{path}"

            return response, url

        path = reverse("api_v1_cli_status_view")
        response, url = get_response(path)
        print(url, response.content)

        path = reverse("api_v1_cli_whoami_view")
        response, url = get_response(path)
        print(url, response.content)

        path = reverse("api_v1_cli_manifest_view", kwargs={"kind": "plugin"})
        response, url = get_response(path)
        print(url, response.content)
