# pylint: disable=W0613
"""Smarter API command-line interface 'delete' view"""

from http import HTTPStatus

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView
from .swagger import (
    COMMON_SWAGGER_PARAMETERS,
    COMMON_SWAGGER_RESPONSES,
    openai_success_response,
)


class ApiV1CliDeleteApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'delete' command in the Smarter command-line interface (CLI).

    The 'delete' command is a Smarter Brokered and Journaled operation that is used with some Smarter resources.

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
        return f"{inherited_class}.ApiV1CliDeleteApiView()"

    @swagger_auto_schema(
        operation_description="""
Executes the 'delete' command for Smarter resources that are not read-only. The resource name is passed in the url query parameters.

This is the API endpoint for the 'delete' command in the Smarter command-line interface (CLI). The 'delete' command is a Smarter Brokered and Journaled operation that is used with some Smarter resources.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object.

This is a brokered operation, so the actual work is delegated to the appropriate broker based on the resource kind specified in the manifest. See smarter.apps.api.v1.cli.brokers.Brokers
""",
        responses={**COMMON_SWAGGER_RESPONSES, HTTPStatus.OK: openai_success_response("Deleted successfully")},
        manual_parameters=[COMMON_SWAGGER_PARAMETERS["kind"], COMMON_SWAGGER_PARAMETERS["name_query_param"]],
    )
    def post(self, request, kind: str, *args, **kwargs):
        response = self.broker.delete(request=request, kwargs=kwargs)
        return response
