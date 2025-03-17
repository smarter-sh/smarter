# pylint: disable=W0613
"""
Smarter API command-line interface 'apply' view
/api/v1/cli/apply/
"""

from django.core.handlers.wsgi import WSGIRequest
from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView


class ApiV1CliApplyApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'apply' command in the Smarter command-line interface (CLI).

    The 'apply' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML manifest in smarter.sh/v1 format.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON object.

    This class is a child of the Django Rest Framework View.
    """

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
        return self.broker.apply(request=request, kwargs=kwargs)
