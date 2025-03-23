# pylint: disable=W0613
"""Smarter API command-line interface 'schema' view"""

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView


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

    def dispatch(self, request, *args, **kwargs):
        self.init(request=request)
        return super().dispatch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="""
Executes the 'schema' command for all Smarter resources.  The resource name is passed in the url query parameters.

This is the API endpoint for the 'schema' command in the Smarter command-line interface (CLI). The 'schema'
command is a Smarter Brokered and Journaled operation that is used with all Smarter resources.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, written in
Golang and available on Windows, macOS, and Linux, or the Smarter web console /docs/

The response from this endpoint is a JSON object containing the published JSON schema.
"""
    )
    def post(self, request, kind: str, *args, **kwargs):
        """
        Handles the POST HTTP request for the 'schema' command.

        Parameters:
        request (Request): The request object. The resource name is passed in the url query parameters.
        *args: Variable length argument list.
        **kwargs: the kind of resource to schema

        Returns:
        Response: A JSON object containing the published JSON schema.
        """
        return self.broker.schema(request=request, kwargs=kwargs)

    def get(self, request, kind: str, *args, **kwargs):
        """
        Handles the GET HTTP request for the 'schema' command.

        Parameters:
        request (Request): The request object. The resource name is passed in the url query parameters.
        *args: Variable length argument list.
        **kwargs: the kind of resource to schema

        Returns:
        Response: A JSON object containing the published JSON schema.
        """
        return self.broker.schema(request=request, kwargs=kwargs)
