# pylint: disable=W0613
"""utility for running api/v1 cli endpoints to verify that they work."""

from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse

from smarter.apps.account.utils import account_admin_user
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER


# pylint: disable=E1101
class Command(BaseCommand):
    """utility for running api/v1 cli endpoints to verify that they work."""

    user = account_admin_user(account=SMARTER_ACCOUNT_NUMBER)

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "username", type=str, nargs="?", default="admin", help="A user associated with the account."
        )

    def handle(self, *args, **options):

        print("Running API CLI endpoints to verify that they work.")
        print("Environment: ", smarter_settings.environment)
        print("Account: ", SMARTER_ACCOUNT_NUMBER)
        print("User: ", self.user.username)

        client = Client()

        url = reverse("api_v1_cli_status_view")
        response = client.post(url)
        print(url, response.content)

        url = reverse("api_v1_cli_whoami_view")
        response = client.post(url)
        print(url, response.content)

        url = reverse("api_v1_cli_manifest_view", kwargs={"kind": "plugin"})
        response = client.post(url)
        print(url, response.content)
