# pylint: disable=W0613,C0302
"""
PromptListView is a Django class-based view that serves the list of ChatBots
for the Smarter workbench web console. It is responsible for fetching the
ChatBots associated with the authenticated user, as well as any shared ChatBots,
and rendering them in a template. The view is protected and requires the user
to be authenticated. It also includes caching to keep the workbench snappy while
avoiding appearing stale.
"""

from django.conf import settings
from django.http import (
    HttpRequest,
)
from django.shortcuts import render
from django.urls import reverse

from smarter.lib import logging
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


class PromptListView(SmarterAuthenticatedWebView):
    """
    list view for smarter workbench web console. This view is protected and
    requires the user to be authenticated. It generates cards for each
    ChatBots.

      id="smarter-prompt-list-root"
      django-csrf-cookie-name="csrftoken"
      django-csrf-token="1UNIA5jlXRTUifBGjVT3yKCn2On8MNzrFiVxN65QVrl6vPZKPx1AC15NcT07RB88"
      django-session-cookie-name="sessionid"
      smarter-prompt-list-api-url="/prompt_list/logs/api/stream/"

    """

    template_path = "react/prompt-list.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        from smarter.apps.prompt.urls import PromptReverseViews

        logger.debug("%s.get() called for %s with args %s, kwargs %s", self.formatted_class_name, request, args, kwargs)
        context = {
            "prompt_list": {
                "root_id": "smarter-prompt-list-root",
                "django_csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "prompt_list_api_url": reverse(
                    ":".join([PromptReverseViews.namespace, PromptReverseViews.listview_api])
                ),
            }
        }

        return render(request, template_name=self.template_path, context=context)
