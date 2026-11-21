# pylint: disable=W0613
"""Utility for applying any Smarter manifest using the api/v1/cli endpoint."""

import os
from typing import Optional

from django.core.management import CommandError
from django.test import RequestFactory

from smarter.apps.account.models import User, UserProfile
from smarter.apps.api.utils import loggable_manifest
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.parsing import parse_manifest

HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getSmarterLogger(__name__)


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
    3. Parse the manifest and find the broker for its kind.
    4. Apply the manifest with that broker, as the user, through a request built with Django's ``RequestFactory``.
    5. Report success, or log the manifest and the broker's response and raise ``CommandError``.

    **Error Handling:**

    The command provides clear error messages for common failure scenarios, such as missing user profiles, invalid manifest input, or unsuccessful API responses. All failures are reported with context to aid trouble shooting.

    **Intended Audience:**

    This tool is intended for developers, system administrators, and anyone interested in learning how Smarter manifests are applied programmatically. It is especially useful for instructional purposes, demonstrations, and manual verification of API endpoint behavior.

    .. seealso::

        - :py:class:`smarter.lib.manifest.broker.abstract_broker_class.AbstractBroker`
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
                logger.debug("using manifest provided on command line.")
                self._data = self.manifest
            elif self.filespec:
                try:
                    with open(self.filespec, encoding="utf-8") as file:
                        self._data = file.read()
                    logger.debug("using manifest from file: %s", self.filespec)
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
            help="relative path a Smarter manifest file (e.g. smarter/llm-clients/llmclient-example.yaml in a clone of https://github.com/smarter-sh/example-manifests).",
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
            "--account_number",
            type=str,
            default=None,
            help=(
                "The account in which to apply the manifest, as the user's profile in it. Without it, the user's "
                "first profile, which is ambiguous for a user who belongs to several accounts."
            ),
        )
        parser.add_argument(
            "--verbose",
            # a flag: with type=bool, any value, even False, turned verbose output on.
            action="store_true",
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
            "handle called with filespec=%s, manifest=%s, username=%s",
            self.filespec,
            loggable_manifest(self.manifest),
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

        account_number = options.get("account_number")
        if account_number:
            # a user, e.g. the Smarter admin, or a department's administrator, may belong to several accounts.
            user_profile = UserProfile.objects.filter(user=self.user, account__account_number=account_number).first()
        else:
            user_profile = UserProfile.get_cached_object(user=self.user)
        if not isinstance(user_profile, UserProfile):
            self.handle_completed_failure(msg="No admin user profile found.")
            return

        logger.debug("applying manifest")

        manifest = parse_manifest(self.data)
        factory = RequestFactory()
        fake_request = factory.post("/fake-url/", data=manifest, content_type="application/json")
        fake_request.user = user_profile.user

        kind = manifest.get("kind")
        if not isinstance(kind, str):
            self.handle_completed_failure(msg="Unable to determine manifest kind.")
            return
        BrokerClass = Brokers.get_broker(kind)
        if BrokerClass is None or not issubclass(BrokerClass, AbstractBroker):
            self.handle_completed_failure(msg=f"No broker found for manifest kind: {kind}")
            return

        broker = BrokerClass(request=fake_request, manifest=manifest, user_profile=user_profile)
        response = broker.apply(request=fake_request)

        if response and response.status_code == 200:
            if verbose:
                logger.debug("manifest applied successfully")
            else:
                logger.debug("manifest applied successfully")
            self.handle_completed_success()
            return
        else:
            # the broker may return no response at all.
            status_code = response.status_code if response is not None else None
            content = response.content.decode("utf-8", errors="replace") if response is not None else None
            self.handle_completed_failure(msg=f"Manifest apply failed with status code: {status_code}")
            logger.error("manifest: %s", loggable_manifest(self.data))
            logger.error("response: %s", content)
            msg = f"Manifest apply failed with status code: {status_code}\nmanifest: {loggable_manifest(self.data)}\nresponse: {content}"
            raise CommandError(msg)
