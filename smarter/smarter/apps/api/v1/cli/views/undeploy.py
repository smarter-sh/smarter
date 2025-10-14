# pylint: disable=W0613
"""Smarter API command-line interface 'undeploy' view"""

from http import HTTPStatus

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView
from .swagger import (
    COMMON_SWAGGER_PARAMETERS,
    COMMON_SWAGGER_RESPONSES,
    openai_success_response,
)


class ApiV1CliUndeployApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'undeploy' command in the Smarter command-line interface (CLI).

    The 'undeploy' command is a Smarter Brokered and Journaled operation that is used with some Smarter resources.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON object containing the results of the operation.

    This class is a child of the Django Rest Framework View.
    """

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.ApiV1CliUndeployApiView()"

    @swagger_auto_schema(
        operation_description="""
Executes the 'undeploy' command for deployable Smarter resources. The resource name is passed in the url query parameters.

This is the API endpoint for the 'undeploy' command in the Smarter command-line interface (CLI). The 'undeploy' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML undeploy in smarter.sh/v1 format.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object containing the results of the operation.

This is a brokered operation, so the actual work is delegated to the appropriate broker based on the resource kind specified in the manifest. See smarter.apps.api.v1.cli.brokers.Brokers
""",
        responses={**COMMON_SWAGGER_RESPONSES, HTTPStatus.OK: openai_success_response("Schema retrieved successfully")},
        manual_parameters=[COMMON_SWAGGER_PARAMETERS["kind"], COMMON_SWAGGER_PARAMETERS["name_query_param"]],
    )
    def post(self, request, kind: str, *args, **kwargs):
        response = self.broker.undeploy(request=request, kwargs=kwargs)
        return response
