# pylint: disable=W0613
"""Smarter API command-line interface 'logs' view."""

from smarter.lib import logging

from .base import CliBaseApiView

logger = logging.getLogger(__name__)


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
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        this_class = f".{ApiV1CliLogsApiView.__name__}[{id(self)}]"
        return f"{inherited_class}{self.formatted_text(this_class)}"

    def post(self, request, kind, *args, **kwargs):
        """
        Return the logs of the resource named in the ``name`` query parameter.

        Brokered and journaled.

        :param request: The request.
        :param kind: The resource's kind, e.g. ``LLMClient``.
        :returns: The journaled json response.
        """
        logger.debug(
            "%s.post() called with request=%s, args=%s, kwargs=%s", self.formatted_class_name, request, args, kwargs
        )
        if self.broker is None:
            raise ValueError(f"No broker found for kind '{kind}' in {self.formatted_class_name}")
        response = self.broker.logs(request=request, kwargs=kwargs)
        return response
