# pylint: disable=W0613,C0302
"""
View for the Dashboard prompt passthrough endpoint.

This module provides an authenticated Django view that renders a React-based
page accepting raw JSON dictionaries formatted for LLM provider APIs. The
frontend submits these payloads directly to the LLM provider via the Smarter
prompt passthrough API, and the API response is rendered back in the template.

The view resolves the correct API and provider-listing URLs at request time and
injects them—along with CSRF and session cookie configuration—into the React
component context.

Classes:
    PromptPassthroughView: Renders the prompt passthrough React page for
        authenticated users.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.passthrough.view import PromptPassthroughView

        urlpatterns = [
            path("passthrough/", PromptPassthroughView.as_view(), name="prompt_passthrough"),
        ]
"""

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from smarter.apps.prompt.api.v1.urls import PromptAPINamespace
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
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
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (chatbot name) and 'kind' (chatbot type).
    :type kwargs: dict

    :returns: Rendered HTML page with chatbot manifest details, or a 404 error page if the chatbot is not found or parameters are invalid.
    :rtype: HttpResponse


    **Example usage**::

        GET /dashboard/passthrough/

    """

    template_path = "prompt/passthrough.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Render the prompt passthrough page for the authenticated user.

        Resolves the LLM provider passthrough API URL and the provider-listing
        API URL at request time, builds a context dictionary for the React
        frontend, and renders ``react/prompt-passthrough.html``.

        The passthrough API URL is derived by stripping the provider-name
        placeholder segment from the fully-qualified URL so that the React
        component can append any provider name dynamically.

        :param request: The incoming HTTP GET request from the client.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments forwarded by the URL dispatcher.
        :param kwargs: Additional keyword arguments forwarded by the URL dispatcher.
        :returns: An HTTP 200 response rendering ``react/prompt-passthrough.html``
            with the passthrough context dictionary.
        :rtype: django.http.HttpResponse
        """
        # pylint: disable=C0415
        from smarter.apps.dashboard.views.passthrough.api.urls import (
            PassthroughApiReverseNames,
        )
        from smarter.apps.dashboard.views.passthrough.urls import (
            PassthroughReverseNames,
        )
        from smarter.apps.dashboard.views.views.urls import DashboardReverseNames

        api_path = reverse(
            ":".join([PromptAPINamespace.namespace, PromptAPINamespace.passthrough]),
            kwargs={"provider_name": "delete-me"},
        )
        api_path = api_path.rstrip("/").rsplit("/", 1)[0] + "/"
        from urllib.parse import urljoin

        from smarter.common.conf import smarter_settings

        api_url = urljoin(smarter_settings.environment_platform_url, api_path)

        provider_api_path = reverse(
            DashboardReverseNames.namespace,
            PassthroughReverseNames.namespace,
            PassthroughApiReverseNames.namespace,
            PassthroughApiReverseNames.api_providers,
        )
        provider_api_url = urljoin(smarter_settings.environment_platform_url, provider_api_path)

        context = {
            "passthrough": {
                "root_id": "smarter-prompt-passthrough-root",
                "csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "api_url": api_url,
                "llm_provider_id": "1",
                "template_id": "1",
                "provider_api_url": provider_api_url,
            }
        }
        self.template_path = "react/prompt-passthrough.html"

        logger.debug(
            "%s.get() rendering Prompt Passthrough View with context: %s",
            self.formatted_class_name,
            logging.formatted_json(context),
        )
        return render(request, self.template_path, context=context)
