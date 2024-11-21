# pylint: disable=W0613
"""Smarter API command-line interface 'get' view"""

import logging

from drf_yasg.utils import swagger_auto_schema

from .base import CliBaseApiView


logger = logging.getLogger(__name__)


class ApiV1CliGetApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'get' command in the Smarter command-line interface (CLI).

    The 'get' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. Get criteria is passed as url query parameters.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON list object.

    This class is a child of the Django Rest Framework View.
    """

    @swagger_auto_schema(
        operation_description="""
Executes the 'get' command for Smarter resources using a YAML manifest in the smarter.sh/v1 format.

This is the API endpoint for the 'get' command in the Smarter command-line interface (CLI). The 'get' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. Get criteria is passed as url query parameters.

The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

The response from this endpoint is a JSON object.
"""
    )
    def post(self, request, kind: str, *args, **kwargs):
        """
        Handles the POST HTTP request for the 'get' command.

        Parameters:
        request (Request): The request object containing a YAML manifest in the smarter.sh/v1 format. Get criteria is passed as url query parameters.
        *args: Variable length argument list.
        **kwargs: the kind of resource to get

        Returns:
        Response: A JSON object representing the result of the 'get' operation.
        """
        logger.info("APIv1CliGetApiView.post() %s", kwargs)
        return self.broker.get(request=request, kwargs=kwargs)
