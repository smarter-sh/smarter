# pylint: disable=W0613
"""Smarter API command-line interface 'logs' view"""

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView
from .const import COMMON_SWAGGER_PARAMETERS, COMMON_SWAGGER_RESPONSES


class ApiV1CliLogsApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'logs' command in the Smarter command-line interface (CLI).

    The 'logs' command is a Smarter Brokered and Journaled operation that is used with some Smarter resources.

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
        return f"{inherited_class}.ApiV1CliLogsApiView()"

    @swagger_auto_schema(
        operation_description="""
Executes the 'logs' command for Smarter resources. The resource name is passed in the url query parameters.

This is the API endpoint for the 'logs' command in the Smarter command-line interface (CLI). The 'logs' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML manifest in smarter.sh/v1 format.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object.
""",
        responses={**COMMON_SWAGGER_RESPONSES, 200: "Logs retrieved successfully"},
        manual_parameters=[COMMON_SWAGGER_PARAMETERS["kind"]],
    )
    def post(self, request, kind, *args, **kwargs):
        response = self.broker.logs(request=request, kwargs=kwargs)
        return response
