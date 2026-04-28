# pylint: disable=W0613,C0302
""" """

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from smarter.apps.prompt.api.v1.urls import PromptAPINamespace
from smarter.lib.django.views import (
    SmarterAuthenticatedNeverCachedWebView,
)

logger = logging.getLogger(__name__)


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
        api_path = reverse(
            ":".join([PromptAPINamespace.namespace, PromptAPINamespace.passthrough]),
            kwargs={"provider_name": "delete-me"},
        )
        api_path = api_path.rstrip("/").rsplit("/", 1)[0] + "/"
        api_url = request.build_absolute_uri(api_path)

        context = {
            "passthrough": {
                "root_id": "smarter-prompt-passthrough-root",
                "csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "api_url": api_url,
                "llm_provider_id": "1",
                "template_id": "1",
            }
        }
        self.template_path = "react/prompt-passthrough.html"

        logger.debug("%s.get() rendering Prompt Passthrough View with context: %s", self.formatted_class_name, context)
        return render(request, self.template_path, context=context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Receives a LLM prompt JSON dict from the frontend and sends this to
        the Provider passthrough service.
        """
        return HttpResponse(status=404)  # Not yet implemented.
