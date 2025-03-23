# pylint: disable=W0613
"""Smarter API command-line interface 'undeploy' view"""

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView


class ApiV1CliUndeployApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'undeploy' command in the Smarter command-line interface (CLI).

    The 'undeploy' command is a Smarter Brokered and Journaled operation that is used with some Smarter resources.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON object containing the results of the operation.

    This class is a child of the Django Rest Framework View.
    """

    @swagger_auto_schema(
        operation_description="""
Executes the 'undeploy' command for deployable Smarter resources. The resource name is passed in the url query parameters.

This is the API endpoint for the 'undeploy' command in the Smarter command-line interface (CLI). The 'undeploy' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. It expects a YAML undeploy in smarter.sh/v1 format.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object containing the results of the operation.
"""
    )
    def post(self, request, kind: str, *args, **kwargs):
        """
        Handles the POST HTTP request for the 'undeploy' command.

        Parameters:
        request (Request): The request object. The resource name is passed in the url query parameters.
        *args: Variable length argument list.
        **kwargs: the kind of resource to undeploy

        Returns:
        Response: a JSON object containing the results of the operation.
        """
        self.init(request=request)
        return self.broker.undeploy(request=request, kwargs=kwargs)
