# pylint: disable=W0613
"""Smarter API command-line interface 'schema' view"""

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView
from .const import COMMON_SWAGGER_PARAMETERS, COMMON_SWAGGER_RESPONSES


class ApiV1CliSchemaApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'schema' command in the Smarter command-line interface (CLI).

    The 'schema' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources.

    The client making the HTTP request to this endpoint is expected to be either the Smarter CLI,
    written in Golang and available on Windows, macOS, and Linux, or the Smarter web console /docs/

    The response from this endpoint is a JSON object containing the published JSON schema.

    This class is a child of the Django Rest Framework View.
    """

    # make this view public
    authentication_classes = ()
    permission_classes = ()

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.ApiV1CliSchemaApiView()"

    @swagger_auto_schema(
        operation_description="""
Executes the 'schema' command for all Smarter resources.  The resource name is passed in the url query parameters.

This is the API endpoint for the 'schema' command in the Smarter command-line interface (CLI). The 'schema'
command is a Smarter Brokered and Journaled operation that is used with all Smarter resources.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, written in
Golang and available on Windows, macOS, and Linux, or the Smarter web console /docs/

The response from this endpoint is a JSON object containing the published JSON schema.
""",
        responses={**COMMON_SWAGGER_RESPONSES, 200: "Schema generated successfully"},
        manual_parameters=[COMMON_SWAGGER_PARAMETERS["kind"]],
    )
    def post(self, request, kind: str, *args, **kwargs):
        return self.broker.schema(request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_description="""
Executes the 'schema' command for all Smarter resources.  The resource name is passed in the url query parameters.

This is the API endpoint for the 'schema' command in the Smarter command-line interface (CLI). The 'schema'
command is a Smarter Brokered and Journaled operation that is used with all Smarter resources.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, written in
Golang and available on Windows, macOS, and Linux, or the Smarter web console /docs/

The response from this endpoint is a JSON object containing the published JSON schema.

This is a brokered operation, so the actual work is delegated to the appropriate broker based on the resource kind specified in the manifest. See smarter.apps.api.v1.cli.brokers.Brokers
""",
        responses={**COMMON_SWAGGER_RESPONSES, 200: "Schema retrieved successfully"},
        manual_parameters=[COMMON_SWAGGER_PARAMETERS["kind"], COMMON_SWAGGER_PARAMETERS["name_query_param"]],
    )
    def get(self, request, kind: str, *args, **kwargs):
        response = self.broker.schema(request=request, kwargs=kwargs)
        return response
