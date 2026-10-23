# pylint: disable=W0613
"""Smarter API command-line interface 'schema' view."""

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

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        this_class = f".{ApiV1CliSchemaApiView.__name__}[{id(self)}]"
        return f"{inherited_class}{self.formatted_text(this_class)}"

    def post(self, request, kind: str, *args, **kwargs):
        """
        Return the JSON Schema of a kind's manifest.

        Brokered and journaled.

        :param request: The request.
        :param kind: The resource's kind, e.g. ``LLMClient``.
        :returns: The journaled json response.
        """
        if self.broker is None:
            raise ValueError(f"No broker found for kind '{kind}' in {self.formatted_class_name}")
        return self.broker.schema(request=request, kwargs=kwargs)

    def get(self, request, kind: str, *args, **kwargs):
        """
        Return the JSON Schema of a kind's manifest.

        Brokered and journaled.

        :param request: The request.
        :param kind: The resource's kind, e.g. ``LLMClient``.
        :returns: The journaled json response.
        """
        if self.broker is None:
            raise ValueError(f"No broker found for kind '{kind}' in {self.formatted_class_name}")
        response = self.broker.schema(request=request, kwargs=kwargs)
        return response
