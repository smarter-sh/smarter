# pylint: disable=W0613
"""utility for running api/v1 cli endpoints to verify that they work."""

import os
from typing import Optional

import yaml
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
from smarter.lib import json
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.drf.models import SmarterAuthToken


HERE = os.path.abspath(os.path.dirname(__file__))


class Command(SmarterCommand):
    """
    Management command for verifying the functionality of ``api/v1/cli/`` endpoints in the Smarter platform.

    This command is designed as both a utility and an instructional tool, allowing developers and administrators to manually exercise and validate the API endpoints that are typically covered by automated unit tests. It provides formatted output to facilitate understanding and troubleshooting.

    **Key Features and Demonstrations:**

    - Shows how to generate an API key for a user, which is required for authenticated API requests.
    - Demonstrates how to include the API key in HTTP requests to ``api/v1/cli/`` endpoints.
    - Explains how to construct and send HTTP requests to various CLI endpoints, including manifest application and plugin operations.
    - Illustrates how to handle and interpret the response objects returned by the API, with formatted output for clarity.

    **Usage:**

    This command is intended to be run via Django's ``manage.py`` interface. It accepts a Smarter account number and a username, retrieves the corresponding user and account, and then performs a series of API endpoint verifications using a single-use API token. The command outputs detailed information about the environment, account, user, and API responses.

    **Workflow:**

    1. Validates the provided account and user information.
    2. Generates a single-use API token for authentication.
    3. Constructs and sends requests to one or more CLI endpoints, displaying the request URLs and responses.
    4. Cleans up by deleting the temporary API token after use.

    **Intended Audience:**

    Developers, QA engineers, and system administrators who need to manually verify API endpoint behavior, troubleshoot issues, or learn how to interact with the Smarter CLI endpoints programmatically. This command is especially useful for demonstrations, manual testing, and instructional purposes.

    .. seealso::

        :py:class:`smarter.apps.api.v1.cli.views.ApiV1CliViewSet` - The viewset containing the CLI endpoints being verified.
        :py:class:`smarter.lib.drf.models.SmarterAuthToken` - The model used for generating API tokens for authentication.
    """

    help = "Run API CLI endpoint verifications."
    _data: Optional[dict] = None

    @property
    def data(self) -> Optional[dict]:
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
        """Run API v1 CLI endpoint verifications."""
        self.handle_begin()

        username = options["username"]
        account_number = options["account_number"]

        account = Account.get_by_account_number(account_number)
        if not account:
            self.handle_completed_failure(msg=f"Account with account number '{account_number}' does not exist.")
            return
        user = get_cached_admin_user_for_account(account=account)
        if username != user.get_username():
            try:
                user_profile = get_cached_user_profile(account=account, user=user)
                if not user_profile:
                    self.handle_completed_failure(
                        msg=f"No user profile for user '{username}' associated with account {account.account_number}."
                    )
                    return
                user = user_profile.user
            except UserProfile.DoesNotExist:
                self.handle_completed_failure(
                    msg=f"No user profile for user '{username}' associated with account {account.account_number}."
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

        def get_response(path, manifest: Optional[str] = None):
            """
            Prepare and get a response from an api/v1/cli endpoint.
            We need to be mindful of the environment we are in, as the
            endpoint may be hosted over https or http.
            """
            client = Client()
            client.force_login(user)

            headers = {"Authorization": f"Token {token_key}"}
            http_host = smarter_settings.environment_platform_domain

            if smarter_settings.environment in SmarterEnvironments.aws_environments:
                response = client.post(
                    path=path, data=manifest, content_type="application/json", HTTP_HOST=http_host, extra=headers
                )
                url = f"https://{smarter_settings.environment_platform_domain}{path}"
            else:
                response = client.post(path=path, data=manifest, content_type="application/json", extra=headers)
                url = f"http://localhost:8000{path}"

            response_content = response.content.decode("utf-8")
            response_json = json.loads(response_content)

            self.stdout.write("url: " + self.style.NOTICE(url))
            response = json.dumps(response_json) + "\n"
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
        self.handle_completed_success()
