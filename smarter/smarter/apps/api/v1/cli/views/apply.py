# pylint: disable=W0613
"""
Smarter API command-line interface 'apply' view
/api/v1/cli/apply/
"""
import logging
from http import HTTPStatus

from django.core.handlers.wsgi import WSGIRequest
from drf_yasg.utils import swagger_auto_schema

from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import APIV1CLIViewError, CliBaseApiView


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING)
        or waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class APIV1CLIViewManifestNotFoundError(APIV1CLIViewError):
    """Custom error for when a manifest is not found."""


class APIV1CLIViewManifestMalFormedError(APIV1CLIViewError):
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
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.ApiV1CliApplyApiView()"

    @swagger_auto_schema(
        operation_description="""
Executes the 'apply' command for Smarter resources using a YAML manifest in the smarter.sh/v1 format.

This is the API endpoint for the 'apply' command in the Smarter command-line interface (CLI). The 'apply' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML manifest in smarter.sh/v1 format.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object.
"""
    )
    def post(self, request: WSGIRequest, *args, **kwargs):
        """
        Handles the POST HTTP request for the 'apply' command.

        Parameters:
        request (Request): The request object containing a YAML manifest in the smarter.sh/v1 format.
        *args: Variable length argument list.
        **kwargs: expected to be an empty dictionary

        Returns:
        Response: A JSON object representing the result of the 'apply' operation.
        """

        if not self.manifest_data:
            raise APIV1CLIViewManifestNotFoundError("No YAML manifest provided.")

        logger.info(
            f"{self.formatted_class_name}.post(): Applying {self.manifest_kind} manifest for {self.manifest_name}"
        )
        response = self.broker.apply(request=request, kwargs=kwargs)
        if response and response.status_code == HTTPStatus.OK:
            logger.info(
                f"{self.formatted_class_name}.post(): Applied {self.manifest_kind} manifest for {self.manifest_name}"
            )
        return response
