# pylint: disable=W0613
"""utility for applying any Smarter manifest using the api/v1/cli endpoint."""

import os
from typing import Optional
from urllib.parse import urljoin

import httpx
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.urls import reverse

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
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

    help = "Apply a Smarter manifest."
    _data: Optional[str] = None
    filespec: Optional[str] = None
    manifest: Optional[str] = None
    user: Optional[User] = None

    @property
    def data(self) -> str:
        """Open and validate the structure of the Manifest data."""

        if self._data is None:
            if self.manifest:
                self.stdout.write("Using manifest provided on command line.")
                self._data = self.manifest
            elif self.filespec:
                try:
                    with open(self.filespec, encoding="utf-8") as file:
                        self._data = file.read()
                    self.stdout.write(f"Using manifest from file: {self.filespec}")
                except FileNotFoundError as e:
                    raise SmarterValueError(f"File not found: {self.filespec}") from e
            if not self._data:
                raise SmarterValueError("Provide either a filespec or a manifest.")
        return self._data

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--filespec",
            type=str,
            nargs="?",
            help="relative path a Smarter manifest file (e.g. smarter/apps/plugin/data/sample-connections/smarter-test-db.yaml).",
        )
        parser.add_argument(
            "--manifest",
            type=str,
            nargs="?",
            help="a Smarter manifest in yaml or json format.",
        )
        parser.add_argument(
            "--username",
            type=str,
            default=None,
            help="Username of the admin user to use when applying the manifest.",
        )
        parser.add_argument(
            "--verbose",
            type=bool,
            default=False,
            help="Enable verbose output.",
        )

    def handle(self, *args, **options):
        """
        Prepare and get a response from the api/v1/cli/apply endpoint.
        We need to be mindful of the environment we are in, as the
        endpoint may be hosted over https or http.
        """
        self.stdout.write(self.style.NOTICE("smarter.apps.api.management.commands.apply_manifest started."))

        self.filespec = options.get("filespec")
        self.manifest = options.get("manifest")
        username = options.get("username")
        verbose = options.get("verbose", False)

        if not isinstance(username, str) or not username.strip():
            self.stderr.write(self.style.ERROR("No username provided."))
            return

        try:
            self.user = User.objects.get(username=username.strip())
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User '{username}' does not exist."))
            return

        user_profile = get_cached_user_profile(user=self.user)
        if not isinstance(user_profile, UserProfile):
            self.stderr.write(self.style.ERROR("No admin user profile found."))
            return

        user = user_profile.user

        try:
            token_record, token_key = SmarterAuthToken.objects.create(  # type: ignore[call-arg]
                name="apply_manifest",
                user=user,
                description="DELETE ME: single-use key created by manage.py apply_manifest",
            )
        # pylint: disable=W0718
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error creating API token: {e}"))
            return

        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.apply, kwargs={})
        url = urljoin(smarter_settings.environment_url, path)
        headers = {"Authorization": f"Token {token_key}", "Content-Type": "application/json"}

        self.stdout.write(
            self.style.NOTICE(
                f"manage.py apply_manifest - Applying manifest via api endpoint {url} as user {user.username} (verbose={verbose})"
            )
        )
        if verbose:
            self.stdout.write(self.style.NOTICE(f"manifest: {self.data}"))
            self.stdout.write(self.style.NOTICE(f"headers: {headers}"))

        self.stdout.write(self.style.NOTICE("Applying manifest ..."))
        httpx_response = httpx.post(url, data=self.data, headers=headers)  # type: ignore[call-arg]
        token_record.delete()

        # wrap up the request
        response_content = httpx_response.content.decode("utf-8")
        if isinstance(response_content, (str, bytearray, bytes)):
            try:
                response_json = json.loads(response_content)
            except json.JSONDecodeError:
                response_json = {"error": "unable to decode response content", "raw": response_content}
        else:
            response_json = {"error": "unable to decode response content"}

        response = json.dumps(response_json) + "\n"
        if httpx_response.status_code == httpx.codes.OK:
            self.stdout.write(self.style.SUCCESS("manifest applied."))
            if verbose:
                self.stdout.write(self.style.SUCCESS(response))
        else:
            self.stderr.write(
                self.style.ERROR(f"Manifest apply to {url} failed with status code: {httpx_response.status_code}")
            )
            self.stderr.write(self.style.ERROR(f"manifest: {self.data}"))
            self.stderr.write(self.style.ERROR(f"response: {response}"))
            msg = f"Manifest apply to {url} failed with status code: {httpx_response.status_code}\nmanifest: {self.data}\nresponse: {response}"
            raise CommandError(msg)

        self.stdout.write(self.style.SUCCESS("smarter.apps.api.management.commands.apply_manifest completed."))
