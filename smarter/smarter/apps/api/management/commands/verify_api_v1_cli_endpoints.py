# pylint: disable=W0613
"""utility for running api/v1 cli endpoints to verify that they work."""

import json

from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import Account, SmarterAuthToken
from smarter.apps.account.utils import account_admin_user
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments
from smarter.lib.django.user import User


class Command(BaseCommand):
    """
    Utility for running api/v1/cli/ endpoints to verify that they work.
    This largely recreates the unit tests for the endpoints, albeit with
    formatted screen output.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "account_number", type=str, nargs="?", default=f"{SMARTER_ACCOUNT_NUMBER}", help="a Smarter account number."
        )
        parser.add_argument(
            "username", type=str, nargs="?", default="admin", help="A user associated with the Smarter account."
        )

    def handle(self, *args, **options):
        username = options["username"]
        account_number = options["account_number"]

        account = Account.get_account_by_number(account_number)
        user = account_admin_user(account=account)
        if username != user.get_username():
            user = User.objects.get(username=username)

        # generate an auth token (api key) for this job.
        token_record, token_key = SmarterAuthToken.objects.create(
            account=account,
            user=user,
            description="DELETE ME: single-use key created by manage.py verify_api_v1_cli_endpoints",
        )

        self.stdout.write(self.style.NOTICE("Running API CLI endpoint verifications."))
        self.stdout.write("*" * 80)
        self.stdout.write("Environment: " + self.style.SUCCESS(f"{smarter_settings.environment}"))
        self.stdout.write("Account: " + self.style.SUCCESS(f"{account_number}"))
        self.stdout.write("User: " + self.style.SUCCESS(f"{user.username}"))
        self.stdout.write("single-use API key: " + self.style.SUCCESS(f"{token_key}"))
        self.stdout.write("*" * 80)

        def get_response(path):
            client = Client()
            client.force_login(user)

            headers = {"Content-Type": "application/json", "Authorization": f"Token {token_key}"}
            http_host = smarter_settings.environment_domain

            if smarter_settings.environment in SmarterEnvironments.aws_environments:
                response = client.post(path=path, HTTP_HOST=http_host, **headers)
                url = f"https://{smarter_settings.environment_domain}{path}"
            else:
                response = client.post(path=path, **headers)
                url = f"http://localhost:8000{path}"

            response_content = response.content.decode("utf-8")
            response_json = json.loads(response_content)

            self.stdout.write("url: " + self.style.NOTICE(url))
            response = json.dumps(response_json, indent=4) + "\n"
            self.stdout.write("response: " + self.style.SUCCESS(response))

        path = reverse("api_v1_cli_status_view")
        get_response(path)

        path = reverse("api_v1_cli_whoami_view")
        get_response(path)

        path = reverse("api_v1_cli_manifest_view", kwargs={"kind": "plugin"})
        get_response(path)

        token_record.delete()
        self.stdout.write(self.style.SUCCESS("API CLI endpoint verifications complete."))
