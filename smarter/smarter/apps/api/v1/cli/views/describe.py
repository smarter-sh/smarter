# pylint: disable=W0613
"""Smarter API command-line interface 'describe' view"""

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView
from .swagger import (
    COMMON_SWAGGER_PARAMETERS,
    COMMON_SWAGGER_RESPONSES,
    EXAMPLE_DESCRIBE_USER,
)

logger = logging.getLogger(__name__)


class ApiV1CliDescribeApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'describe' command in the Smarter command-line interface (CLI).

    The 'describe' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON object containing the resource manifest.

    This class is a child of the Django Rest Framework View.
    """

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.{ApiV1CliDescribeApiView.__name__}[{id(self)}]"

    @swagger_auto_schema(operation_description="""
Executes the 'describe' command for all Smarter resources.  The resource name is passed in the url query parameters.

This is the API endpoint for the 'describe' command in the Smarter command-line interface (CLI). The 'describe' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML manifest in smarter.sh/v1 format.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object containing a representation of the resource manifest.
""")
    def post(self, request, kind: str, *args, **kwargs):
        logger.debug(
            "%s.post() called with request=%s, args=%s, kwargs=%s", self.formatted_class_name, request, args, kwargs
        )
        response = self.broker.describe(request, *args, **kwargs)
        return response

    @swagger_auto_schema(
        operation_description="""
Executes the 'describe' command for Smarter resources. The resource name is passed in the url query parameters.

This is the API endpoint for the 'describe' command in the Smarter command-line interface (CLI). The 'describe' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML manifest in smarter.sh/v1 format.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object containing a representation of the resource manifest.

This is a brokered operation, so the actual work is delegated to the appropriate broker based on the resource kind specified in the manifest. See smarter.apps.api.v1.cli.brokers.Brokers
""",
        responses={
            **COMMON_SWAGGER_RESPONSES,
            200: openapi.Response(
                description="User admin described successfully",
                examples=EXAMPLE_DESCRIBE_USER,
            ),
        },
        manual_parameters=[COMMON_SWAGGER_PARAMETERS["kind"], COMMON_SWAGGER_PARAMETERS["name_query_param"]],
    )
    def get(self, request, kind, *args, **kwargs):

        logger.debug(
            "%s.get() called with request=%s, args=%s, kwargs=%s", self.formatted_class_name, request, args, kwargs
        )
        response = self.broker.describe(request, *args, **kwargs)
        return response
