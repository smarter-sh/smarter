# pylint: disable=W0613
"""utility for running api/v1 cli endpoints to verify that they work."""

import json

from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import Account
from smarter.apps.account.utils import account_admin_user
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments


class Command(BaseCommand):
    """utility for running api/v1 cli endpoints to verify that they work."""

    account = Account.get_account_by_number(SMARTER_ACCOUNT_NUMBER)
    user = account_admin_user(account=account)

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "username", type=str, nargs="?", default="admin", help="A user associated with the Smarter account."
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

            if smarter_settings.environment in SmarterEnvironments.aws_environments:
                response = client.post(path=path, HTTP_HOST=smarter_settings.environment_domain)
                url = f"https://{smarter_settings.environment_domain}{path}"
            else:
                response = client.post(path=path)
                url = f"http://localhost:8000{path}"

            response_content = response.content.decode("utf-8")
            response_json = json.loads(response_content)

            print("url: ", url)
            print("response: ", json.dumps(response_json, indent=4), "\n")

        path = reverse("api_v1_cli_status_view")
        get_response(path)

        path = reverse("api_v1_cli_whoami_view")
        get_response(path)

        path = reverse("api_v1_cli_manifest_view", kwargs={"kind": "plugin"})
        get_response(path)
