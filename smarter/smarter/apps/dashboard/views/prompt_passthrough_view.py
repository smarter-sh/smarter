# pylint: disable=W0613,C0302
""" """

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from smarter.lib.django.views import (
    SmarterAuthenticatedNeverCachedWebView,
)


class PromptPassthroughView(SmarterAuthenticatedNeverCachedWebView):
    """
    Renders a passthrough template for the prompt app that accepts a raw JSON
    dict for an LLM provider, passes this directly to the LLM provider API,
    and renders the API response in the template.

    :param request: Django HTTP request object.
    :type request: WSGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (chatbot name) and 'kind' (chatbot type).
    :type kwargs: dict

    :returns: Rendered HTML page with chatbot manifest details, or a 404 error page if the chatbot is not found or parameters are invalid.
    :rtype: HttpResponse


    **Example usage**::

        GET /chatbot/detail/?name=my_chatbot&kind=custom

    """

    template_path = "prompt/passthrough.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        View for rendering the Monaco terminal emulation page
        which only receives JSON dicts of LLM prompts.
        """

        context = {"page_title": "Terminal"}
        self.template_path = "react/prompt-passthrough.html"
        return render(request, self.template_path, context=context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Receives a LLM prompt JSON dict from the frontend and sends this to
        the Provider passthrough service.
        """
        return HttpResponse(status=404)  # Not yet implemented.
