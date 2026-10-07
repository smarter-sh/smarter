# pylint: disable=W0613
"""
Smarter API command-line interface 'apply' view.

/api/v1/cli/apply/
"""

from http import HTTPStatus

import yaml
from django.core.handlers.asgi import ASGIRequest
from drf_yasg.utils import swagger_auto_schema

from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import APIV1CLIViewBadRequestError, APIV1CLIViewError, CliBaseApiView
from .swagger import (
    COMMON_SWAGGER_RESPONSES,
    ManifestSerializer,
    openai_success_response,
)

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.API_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)


class APIV1CLIViewManifestNotFoundError(APIV1CLIViewBadRequestError):
    """Custom error for when a manifest is not found."""


class APIV1CLIViewManifestMalFormedError(APIV1CLIViewBadRequestError):
    """Custom error for when a manifest is malformed."""


class ApiV1CliApplyApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'apply' command in the Smarter command-line interface (CLI).

    The 'apply' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML manifest in smarter.sh/v1 format.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON object.

    This class is a child of the Django Rest Framework View.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        this_class = f".{ApiV1CliApplyApiView.__name__}[{id(self)}]"
        return f"{inherited_class}{self.formatted_text(this_class)}"

    def raise_for_unparseable_manifest(self, request: ASGIRequest) -> None:
        """Raise a malformed manifest error if the request body is text that is not a YAML or JSON object."""
        try:
            body = request.body.decode("utf-8")
        # pylint: disable=broad-except
        except Exception:
            return
        if not body.strip():
            return
        try:
            parsed = yaml.safe_load(body)
        except yaml.YAMLError as e:
            raise APIV1CLIViewManifestMalFormedError(f"The manifest is not valid YAML: {e}") from e
        if not isinstance(parsed, dict):
            raise APIV1CLIViewManifestMalFormedError(
                f"The manifest must be a YAML object with apiVersion, kind, metadata and spec, not a {type(parsed).__name__}."
            )

    @swagger_auto_schema(
        operation_description="""
Executes the 'apply' command for Smarter resources using a YAML manifest in the smarter.sh/v1 format.

This is the API endpoint for the 'apply' command in the Smarter command-line interface (CLI). The 'apply' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML manifest in smarter.sh/v1 format.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object.

This is a brokered operation, so the actual work is delegated to the appropriate broker based on the resource kind specified in the manifest. See smarter.apps.api.v1.cli.brokers.Brokers
""",
        responses={**COMMON_SWAGGER_RESPONSES, HTTPStatus.OK: openai_success_response("Manifest applied successfully")},
        request_body=ManifestSerializer,
    )
    def post(self, request: ASGIRequest, *args, **kwargs):
        """Handles POST requests to apply a Smarter manifest."""

        logger.debug(
            "%s.post() called with request=%s, args=%s, kwargs=%s", self.formatted_class_name, request, args, kwargs
        )

        if not self.manifest_data:
            self.raise_for_unparseable_manifest(request)
            raise APIV1CLIViewManifestNotFoundError("No YAML manifest provided.")

        user = kwargs.pop("user", None)
        account = kwargs.pop("account", None)
        user_profile = kwargs.pop("user_profile", None)
        if self.broker is None:
            if self.loader is None or not self.loader.ready:
                # the broker could not be instantiated because the manifest itself is
                # not valid, which is the client's error, a 400, rather than a 500.
                raise SmarterValueError(
                    f"The {self.manifest_kind} manifest is not valid: it must have an apiVersion, kind, "
                    "metadata and a non-empty spec."
                )
            raise APIV1CLIViewError(f"No broker found for manifest kind '{self.manifest_kind}'.")
        response = self.broker.apply(
            request, user=user, account=account, user_profile=user_profile, args=args, kwargs=kwargs
        )
        if response and response.status_code == HTTPStatus.OK:
            logger.debug(
                "%s.post(): Applied %s manifest for %s",
                self.formatted_class_name,
                self.manifest_kind,
                self.manifest_name,
            )
        return response
