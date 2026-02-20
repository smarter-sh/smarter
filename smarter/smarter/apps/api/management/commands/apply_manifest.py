# pylint: disable=W0613
"""utility for applying any Smarter manifest using the api/v1/cli endpoint."""

import logging
import os
from typing import Optional

from django.core.management import CommandError
from django.test import RequestFactory

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.loader import SAMLoader

HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}")


class Command(SmarterCommand):
    """
    Utility for running ``api/v1/cli/`` endpoints to verify their functionality.

    This management command serves both as a utility and an instructional tool for interacting with Smarter manifests via the API. It is designed to help developers and administrators understand and validate the process of applying manifests through the CLI endpoint.

    **Key Features and Demonstrations:**

    - Shows how to generate an API key for a user, which is required for authenticated requests.
    - Demonstrates how to include the API key in HTTP requests to ``api/v1/cli/`` endpoints.
    - Explains how to construct and send HTTP requests to the manifest application endpoint.
    - Illustrates how to handle and interpret the response object returned by the API.

    **Usage:**

    This command can be invoked via Django's ``manage.py`` interface. It accepts either a manifest file (YAML or JSON) or a manifest string directly, along with the username of the admin user who will apply the manifest. The command will:

    1. Validate the provided manifest input.
    2. Retrieve the specified user and ensure they have an associated admin profile.
    3. Generate a single-use API token for authentication.
    4. Construct the appropriate API endpoint URL, considering the current environment (HTTP/HTTPS).
    5. Send the manifest data to the API endpoint using an authenticated HTTP POST request.
    6. Display formatted output, including request details and the API response, with optional verbosity.

    **Error Handling:**

    The command provides clear error messages for common failure scenarios, such as missing user profiles, invalid manifest input, or unsuccessful API responses. All failures are reported with context to aid trouble shooting.

    **Intended Audience:**

    This tool is intended for developers, system administrators, and anyone interested in learning how Smarter manifests are applied programmatically. It is especially useful for instructional purposes, demonstrations, and manual verification of API endpoint behavior.

    .. seealso::

        - :py:class:`smarter.apps.api.v1.cli.urls.ApiV1CliReverseViews`
        - :py:class:`smarter.lib.drf.models.SmarterAuthToken`

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
                logger.debug("%s - using manifest provided on command line.", logger_prefix)
                self._data = self.manifest
            elif self.filespec:
                try:
                    with open(self.filespec, encoding="utf-8") as file:
                        self._data = file.read()
                    logger.debug("%s - using manifest from file: %s", logger_prefix, self.filespec)
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
        self.handle_begin()

        self.filespec = options.get("filespec")
        self.manifest = options.get("manifest")
        username = options.get("username")
        verbose = options.get("verbose", False)

        logger.debug(
            "%s - handle called with filespec=%s, manifest=%s, username=%s",
            logger_prefix,
            self.filespec,
            self.manifest,
            username,
        )

        if not isinstance(username, str) or not username.strip():
            self.handle_completed_failure(msg="No username provided.")
            return

        try:
            self.user = User.objects.get(username=username.strip())
        except User.DoesNotExist as e:
            self.handle_completed_failure(e, msg=f"User '{username}' does not exist.")
            return

        user_profile = get_cached_user_profile(user=self.user)
        if not isinstance(user_profile, UserProfile):
            self.handle_completed_failure(msg="No admin user profile found.")
            return

        # user = user_profile.user

        # try:
        #     token_record, token_key = SmarterAuthToken.objects.create(  # type: ignore[call-arg]
        #         account=user_profile.account,
        #         name="apply_manifest",
        #         user=user,
        #         description="DELETE ME: single-use key created by manage.py apply_manifest",
        #     )
        #     logger.debug("%s - created single-use token %s for user %s", logger_prefix, token_key, user_profile)
        # # pylint: disable=W0718
        # except Exception as e:
        #     self.handle_completed_failure(e, msg=f"Error creating API token: {e}")
        #     return

        # path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.apply, kwargs={})
        # url = urljoin(smarter_settings.environment_url, path)
        # headers = {"Authorization": f"Token {token_key}", "Content-Type": "application/json"}

        # msg = f"{logger_prefix} applying manifest (verbose={verbose}) url={url} as user={user_profile} headers={headers}  data={self.data}"
        # logger.debug("%s - %s", logger_prefix, msg)
        # if verbose:
        #     logger.debug("%s manifest: %s", logger_prefix, self.data)
        #     logger.debug("%s headers: %s", logger_prefix, headers)

        logger.debug("%s - applying manifest", logger_prefix)

        # ----------------------------------------------------------------------
        # PLAN B
        # ----------------------------------------------------------------------
        loader = SAMLoader(manifest=self.data)
        factory = RequestFactory()
        fake_request = factory.post("/fake-url/", data=loader.manifest, content_type="application/json")
        fake_request.user = user_profile.user

        if not isinstance(loader.kind, str):
            self.handle_completed_failure(msg="Unable to determine manifest kind.")
            return
        BrokerClass = Brokers.get_broker(loader.kind)
        if BrokerClass is None or not issubclass(BrokerClass, AbstractBroker):
            self.handle_completed_failure(msg=f"No broker found for manifest kind: {loader.kind}")
            return

        broker = BrokerClass(request=fake_request, loader=loader, user_profile=user_profile)
        response = broker.apply(request=fake_request)

        if response.status_code == 200:
            if verbose:
                logger.debug("%s - manifest applied successfully", logger_prefix)
            else:
                logger.debug("%s - manifest applied successfully", logger_prefix)
            self.handle_completed_success()
            return
        else:
            self.handle_completed_failure(msg=f"Manifest apply failed with status code: {response.status_code}")
            logger.error("%s - manifest: %s", logger_prefix, self.data)
            logger.error("%s - response: %s", logger_prefix, response.content)
            msg = f"Manifest apply failed with status code: {response.status_code}\nmanifest: {self.data}\nresponse: {response.content}"
            raise CommandError(msg)

        # ----------------------------------------------------------------------
        # PLAN B
        # ----------------------------------------------------------------------
        # try:
        #     httpx_response = httpx.post(url, content=self.data, headers=headers)
        # except httpx.HTTPError as e:
        #     self.handle_completed_failure(e, msg=f"HTTP error applying manifest to {url}: {e}")
        #     return
        # finally:
        #     token_record.delete()

        # wrap up the request
        # response_content = httpx_response.content.decode("utf-8")
        # if isinstance(response_content, (str, bytearray, bytes)):
        #     try:
        #         response_json = json.loads(response_content)
        #     except json.JSONDecodeError:
        #         response_json = {"error": "unable to decode response content", "raw": response_content}
        # else:
        #     response_json = {"error": "unable to decode response content"}

        # response = json.dumps(response_json) + "\n"
        # if httpx_response.status_code == httpx.codes.OK:
        #     if verbose:
        #         logger.debug("%s - manifest apply response: %s", logger_prefix, response)
        #     else:
        #         logger.debug("%s - manifest applied successfully", logger_prefix)
        # else:
        #     self.handle_completed_failure(
        #         msg=f"Manifest apply to {url} failed with status code: {httpx_response.status_code}"
        #     )
        #     logger.error("%s - manifest: %s", logger_prefix, self.data)
        #     logger.error("%s - response: %s", logger_prefix, response)
        #     msg = f"Manifest apply to {url} failed with status code: {httpx_response.status_code}\nmanifest: {self.data}\nresponse: {response}"
        #     raise CommandError(msg)

        # self.handle_completed_success()
