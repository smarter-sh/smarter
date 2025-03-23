# pylint: disable=W0613
"""Smarter API command-line interface 'delete' view"""

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView


class ApiV1CliDeleteApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'delete' command in the Smarter command-line interface (CLI).

    The 'delete' command is a Smarter Brokered and Journaled operation that is used with some Smarter resources.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON object.

    This class is a child of the Django Rest Framework View.
    """

    @swagger_auto_schema(
        operation_description="""
Executes the 'delete' command for Smarter resources that are not read-only. The resource name is passed in the url query parameters.

This is the API endpoint for the 'delete' command in the Smarter command-line interface (CLI). The 'delete' command is a Smarter Brokered and Journaled operation that is used with some Smarter resources.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object.
"""
    )
    def post(self, request, kind: str, *args, **kwargs):
        """
        Handles the POST HTTP request for the 'delete' command.

        Parameters:
        request (Request): The request object. The resource name is passed in the url query parameters.
        *args: Variable length argument list.
        **kwargs: the kind of resource to delete

        Returns:
        Response: A JSON object representing the result of the 'delete' operation.
        """
        self.init(request=request)
        return self.broker.delete(request=request, kwargs=kwargs)
