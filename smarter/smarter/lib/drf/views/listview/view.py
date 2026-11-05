# pylint: disable=W0613
"""The web console page that hosts the React list app of the user's API keys (AuthTokens)."""

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.shortcuts import render

from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active
from smarter.lib.drf.models import SmarterAuthToken as AuthToken

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.SECRET_LOGGING])


class AuthTokenListView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the API key list page of the Smarter Workbench web console.

    The page hosts the ``smarter-authtoken-list`` React app, which lists the API keys available to
    the authenticated user, from :class:`~smarter.lib.drf.views.listview.api.AuthTokenListApiView`.
    """

    template_path = "react/authtoken-list.html"
    authtokens: list[AuthToken]

    @property
    def formatted_class_name(self) -> str:
        """The view's dotted class name and instance id, formatted for log messages."""
        class_name = f"{__name__}.{AuthTokenListView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: ASGIRequest, *args, **kwargs):
        """
        Render the page that hosts the API key list React app, with its configuration in the context.

        :param request: The request.
        :param args: Positional arguments from the url, unused.
        :param kwargs: Keyword arguments from the url, unused.
        :returns: The rendered page.
        """
        # pylint: disable=C0415
        from smarter.lib.drf.urls import AuthTokenReverseNames

        context = {
            "authtoken_list": {
                "root_id": "smarter-authtoken-list-root",
                "django_csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "authtoken_list_api_url": reverse(
                    AuthTokenReverseNames.namespace, AuthTokenReverseNames.listview_api_all
                ),
                "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
                "smarter_request_id": self.generate_smarter_request_id(),
            }
        }

        logger.debug(
            "%s.get() called for %s with args %s, kwargs %s with context %s",
            self.formatted_class_name,
            request,
            args,
            kwargs,
            logging.SmarterFormattedText.json(context),
        )
        return render(request, template_name=self.template_path, context=context)
