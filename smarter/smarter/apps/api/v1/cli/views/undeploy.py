# pylint: disable=W0613
"""Smarter API command-line interface 'undeploy' view."""

from smarter.lib import logging

from .base import CliBaseApiView

logger = logging.getLogger(__name__)


class ApiV1CliUndeployApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'undeploy' command in the Smarter command-line interface (CLI).

    The 'undeploy' command is a Smarter Brokered and Journaled operation that is used with some Smarter resources.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON object containing the results of the operation.

    This class is a child of the Django Rest Framework View.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.{ApiV1CliUndeployApiView.__name__}[{id(self)}]"

    def post(self, request, kind: str, *args, **kwargs):
        """
        Undeploy the resource of a kind whose name is in the ``name`` query parameter.

        Brokered and journaled.

        :param request: The request.
        :param kind: The resource's kind, e.g. ``LLMClient``.
        :returns: The journaled json response.
        """
        logger.debug(
            "%s.post() called with request=%s, args=%s, kwargs=%s", self.formatted_class_name, request, args, kwargs
        )
        response = self.broker.undeploy(request=request, kwargs=kwargs)
        return response
