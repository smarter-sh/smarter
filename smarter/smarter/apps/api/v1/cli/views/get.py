# pylint: disable=W0613
"""Smarter API command-line interface 'get' view."""

from smarter.lib import logging
from smarter.lib.annotation.const import ANNOTATION_SELECTOR_PARAM
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import CliBaseApiView

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.API_LOGGING])


class ApiV1CliGetApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'get' command in the Smarter command-line interface (CLI).

    The 'get' command is a Smarter Brokered and Journaled operation that is used with all Smarter resources. Get criteria is passed as url query parameters.

    The client making the HTTP request to this endpoint is expected to be the Smarter CLI, which is written in Golang and available on Windows, macOS, and Linux.

    The response from this endpoint is a JSON list object.

    This class is a child of the Django Rest Framework View.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        this_class = f".{ApiV1CliGetApiView.__name__}[{id(self)}]"
        return f"{inherited_class}{self.formatted_text(this_class)}"

    def post(self, request, kind: str, *args, **kwargs):
        """
        List the resources of a kind that the requester may read.

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
        # the get criteria, e.g. ?name=..., are the url's query parameters. Brokers read them
        # from their keyword arguments. An annotation selector may be repeated, so it is a list.
        params = {key: self.params.get(key) for key in self.params} if self.params else {}
        if self.params and ANNOTATION_SELECTOR_PARAM in self.params:
            params[ANNOTATION_SELECTOR_PARAM] = self.params.getlist(ANNOTATION_SELECTOR_PARAM)
        response = self.broker.get(request, *args, **{**kwargs, **params})
        return response
