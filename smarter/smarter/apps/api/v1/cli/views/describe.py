# pylint: disable=W0613
"""Smarter API command-line interface 'describe' view"""

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView


class ApiV1CliDescribeApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'describe' command in the Smarter command-line interface (CLI).

    The 'describe' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON object containing the resource manifest.

    This class is a child of the Django Rest Framework View.
    """

    @swagger_auto_schema(
        operation_description="""
Executes the 'describe' command for all Smarter resources.  The resource name is passed in the url query parameters.

This is the API endpoint for the 'describe' command in the Smarter command-line interface (CLI). The 'describe' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML manifest in smarter.sh/v1 format.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object containing the resource manifest.
"""
    )
    def post(self, request, kind: str, *args, **kwargs):
        """
        Handles the POST HTTP request for the 'describe' command.

        Parameters:
        request (Request): The request object. The resource name is passed in the url query parameters.
        *args: Variable length argument list.
        **kwargs: the kind of resource to describe

        Returns:
        Response: A JSON object containing the resource manifest.
        """
        return self.broker.describe(request=request, kwargs=kwargs)
