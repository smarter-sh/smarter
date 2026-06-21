# pylint: disable=W0613
"""
This module contains views to implement the React.

AuthToken list view in the Smarter Dashboard.
"""

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
    Render the authtoken list view for the Smarter Workbench web console.

    This view displays all authtokens available to the authenticated user as cards, providing a quick overview and access to authtoken details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each authtoken, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    template_path = "react/authtoken-list.html"
    authtokens: list[AuthToken]

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{AuthTokenListView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: ASGIRequest, *args, **kwargs):
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
                "smarter_request_id": self.smarter_request_id(),
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
