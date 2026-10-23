# pylint: disable=W0613
"""Smarter API command-line interface 'example_manifest' view."""

from django.http import HttpResponseNotAllowed

from smarter.common.const import SmarterHttpMethods
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import CliBaseApiView

logger = logging.getLogger(__name__)


class ApiV1CliManifestApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'example_manifest' command in the Smarter command-line interface (CLI).

    It generates an example manifest for a specified Smarter resource.

    The 'example_manifest' command is a Smarter Brokered and Journaled operation that is used with some Smarter resources.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI,
    which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON object containing an example manifest of the resource.

    This class is a child of the Django Rest Framework View.
    """

    # make this view public
    authentication_classes = ()
    permission_classes = ()

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        this_class = f".{ApiV1CliManifestApiView.__name__}[{id(self)}]"
        return f"{inherited_class}{self.formatted_text(this_class)}"

    def post(self, request, kind, *args, **kwargs):
        """
        Return an example manifest of a kind.

        Brokered and journaled.

        :param request: The request.
        :param kind: The resource's kind, e.g. ``LLMClient``.
        :returns: The journaled json response.
        """
        if self.broker is None:
            raise ValueError(f"No broker found for kind '{kind}' in {self.formatted_class_name}")
        return self.broker.example_manifest(request=request, kwargs=kwargs)

    def get(self, request, kind, *args, **kwargs):
        """
        Return an example manifest of a kind.

        Brokered and journaled.

        :param request: The request.
        :param kind: The resource's kind, e.g. ``LLMClient``.
        :returns: The journaled json response.
        """
        logger.debug(
            "%s.get() called with request=%s, args=%s, kwargs=%s", self.formatted_class_name, request, args, kwargs
        )
        if not waffle.switch_is_active(SmarterWaffleSwitches.ALLOW_API_GET):
            logger.error(
                "%s.get() is not allowed because %s switch is inactive.",
                self.formatted_class_name,
                SmarterWaffleSwitches.ALLOW_API_GET,
            )
            return HttpResponseNotAllowed(permitted_methods=[SmarterHttpMethods.POST])

        if self.broker is None:
            raise ValueError(f"No broker found for kind '{kind}' in {self.formatted_class_name}")

        response = self.broker.example_manifest(request=request, kwargs=kwargs)
        return response
