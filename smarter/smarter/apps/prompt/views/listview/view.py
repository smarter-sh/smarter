# pylint: disable=W0613,C0302
"""
PromptListView is a Django class-based view that serves the list of LLMClients.

for the Smarter workbench web console. It is responsible for fetching the
LLMClients associated with the authenticated user, as well as any shared LLMClients,
and rendering them in a template. The view is protected and requires the user
to be authenticated. It also includes caching to keep the workbench snappy while
avoiding appearing stale.
"""

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import render

from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


class PromptListView(SmarterAuthenticatedWebView):
    """
    List view for smarter workbench web console.

    This sets up
    the React component that will render the list of LLMClients. The React
    component uses the views located in ./api for its data.

      id="smarter-prompt-list-root"
      django-csrf-cookie-name="csrftoken"
      django-session-cookie-name="sessionid"
      smarter-prompt-list-api-url="/prompt/api/llm-clients/"
    """

    template_path = "react/prompt-list.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PromptListView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        # pylint: disable=C0415
        from smarter.apps.prompt.urls import PromptReverseNames

        context = {
            "prompt_list": {
                "root_id": "smarter-prompt-list-root",
                "django_csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "prompt_list_api_url": reverse(PromptReverseNames.namespace, PromptReverseNames.listview_api_all),
            }
        }

        logger.debug(
            "%s.get() called for %s with args %s, kwargs %s with context %s",
            self.formatted_class_name,
            request,
            args,
            kwargs,
            logging.formatted_json(context),
        )
        return render(request, template_name=self.template_path, context=context)
