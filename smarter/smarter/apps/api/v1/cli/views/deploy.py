# pylint: disable=W0613
"""Smarter API command-line interface 'deploy' view"""

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView
from .const import (
    COMMON_SWAGGER_PARAMETERS,
    COMMON_SWAGGER_RESPONSES,
    ManifestSerializer,
)


class ApiV1CliDeployApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'deploy' command in the Smarter command-line interface (CLI).

    The 'deploy' command is a Smarter Brokered and Journaled operation that is used with any deployable Smarter resource.

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
        return f"{inherited_class}.ApiV1CliDeployApiView()"

    @swagger_auto_schema(
        operation_description="""
Executes the 'deploy' command for applicable Smarter resources. The resource name is passed in the url query parameters.

This is the API endpoint for the 'deploy' command in the Smarter command-line interface (CLI). The 'deploy' command is a Smarter Brokered and Journaled operation that is used with any deployable Smarter resource.  The resource name is passed in the url query parameters.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object.

This is a brokered operation, so the actual work is delegated to the appropriate broker based on the resource kind specified in the manifest. See smarter.apps.api.v1.cli.brokers.Brokers
""",
        responses={**COMMON_SWAGGER_RESPONSES, 200: "Deployed successfully"},
        manual_parameters=[COMMON_SWAGGER_PARAMETERS["kind"], COMMON_SWAGGER_PARAMETERS["name_query_param"]],
    )
    def post(self, request, kind: str, *args, **kwargs):
        response = self.broker.deploy(request=request, kwargs=kwargs)
        return response
