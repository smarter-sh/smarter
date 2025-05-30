# pylint: disable=W0613
"""utility for running api/v1 cli endpoints to verify that they work."""

import json
import os

import yaml
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    get_cached_user_profile,
)
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments
from smarter.lib.drf.models import SmarterAuthToken


HERE = os.path.abspath(os.path.dirname(__file__))


class Command(BaseCommand):
    """
    Utility for running api/v1/cli/ endpoints to verify that they work.
    This largely recreates the unit tests for the endpoints, albeit with
    formatted screen output.

    This is an instructional tool as much as a utility, demonstrating the
    following:
    - how to generate an API key for a user
    - how to add the API key to an http request to api/v1/cli/ endpoints
    - how to setup an http request for an api/v1/cli/ endpoint
    - how to work with the response object
    """

    help = "Run API CLI endpoint verifications."
    _data: str = None

    @property
    def data(self) -> json:
        """Return the plugin.yaml data."""
        if self._data is None:
            file_path = os.path.join(HERE, "data", "plugin.yaml")
            with open(file_path, encoding="utf-8") as file:
                data = file.read()
                self._data = yaml.safe_load(data)
        return self._data

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

        account = Account.get_by_account_number(account_number)
        user = get_cached_admin_user_for_account(account=account)
        if username != user.get_username():
            try:
                user_profile = get_cached_user_profile(account=account, user=user)
                user = user_profile.user
            except UserProfile.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"No user '{username}' associated with account {account.account_number}.")
                )
                return

        # generate an auth token (api key) for this job.
        token_record, token_key = SmarterAuthToken.objects.create(
            name="verify_api:v1:cli:endpoints",
            user=user,
            description="DELETE ME: single-use key created by manage.py verify_api:v1:cli:endpoints",
        )

        self.stdout.write(self.style.NOTICE("Running API CLI endpoint verifications."))
        self.stdout.write("*" * 80)
        self.stdout.write("Environment: " + self.style.SUCCESS(f"{smarter_settings.environment}"))
        self.stdout.write("Account: " + self.style.SUCCESS(f"{account_number}"))
        self.stdout.write("User: " + self.style.SUCCESS(f"{user.username}"))
        self.stdout.write("single-use API key: " + self.style.SUCCESS(f"{token_key}"))
        self.stdout.write("*" * 80)

        def get_response(path, manifest: str = None):
            """
            Prepare and get a response from an api/v1/cli endpoint.
            We need to be mindful of the environment we are in, as the
            endpoint may be hosted over https or http.
            """
            client = Client()
            client.force_login(user)

            headers = {"Authorization": f"Token {token_key}"}
            http_host = smarter_settings.environment_domain

            if smarter_settings.environment in SmarterEnvironments.aws_environments:
                response = client.post(
                    path=path, data=manifest, content_type="application/json", HTTP_HOST=http_host, extra=headers
                )
                url = f"https://{smarter_settings.environment_domain}{path}"
            else:
                response = client.post(path=path, data=manifest, content_type="application/json", extra=headers)
                url = f"http://localhost:8000{path}"

            response_content = response.content.decode("utf-8")
            response_json = json.loads(response_content)

            self.stdout.write("url: " + self.style.NOTICE(url))
            response = json.dumps(response_json, indent=4) + "\n"
            self.stdout.write("response: " + self.style.SUCCESS(response))

        path = reverse(ApiV1CliReverseViews.namespace + "apply_view", kwargs={})
        get_response(path, manifest=self.data)

        # path = reverse("api:v1:cli:deploy_view", kwargs={"kind": "plugin", "name": "PluginVerification"})
        # get_response(path)

        # path = reverse("api:v1:cli:describe_view", kwargs={"kind": "plugin", "name": "PluginVerification"})
        # get_response(path)

        # path = reverse("api:v1:cli:logs_kind_name_view", kwargs={"kind": "plugin", "name": "PluginVerification"})
        # get_response(path)

        # path = reverse("api:v1:cli:get_view", kwargs={"kind": "plugins"})
        # get_response(path)

        # path = reverse("api:v1:cli:delete_view", kwargs={"kind": "plugin", "name": "PluginVerification"})
        # get_response(path)

        # path = reverse("api:v1:cli:manifest_view", kwargs={"kind": "plugin"})
        # get_response(path)

        # path = reverse("api:v1:cli:status_view")
        # get_response(path)

        # path = reverse("api:v1:cli:whoami_view")
        # get_response(path)

        token_record.delete()
        self.stdout.write(self.style.SUCCESS("API CLI endpoint verifications complete."))
