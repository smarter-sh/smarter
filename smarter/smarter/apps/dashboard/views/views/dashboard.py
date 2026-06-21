# pylint: disable=W0613
"""
Main dashboard view.

This module provides the primary authenticated dashboard view that renders the
React-based dashboard page. Responses are lightly cached on a per-user basis
(``DASHBOARD_CACHE_TIMEOUT`` seconds) to keep the UI snappy without serving
stale data.

Unauthenticated requests are redirected to the login page.

Attributes:
    DASHBOARD_CACHE_TIMEOUT (int): Per-user response cache lifetime in seconds
        (default: ``10``).

Classes:
    DashboardView: Authenticated, lightly cached view that renders the React
        dashboard page.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.views.dashboard import DashboardView

        urlpatterns = [
            path("", DashboardView.as_view(), name="dashboard"),
        ]
"""

from django.conf import settings
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import redirect, render

from smarter.common.utils import is_authenticated_request
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getLogger(__name__)
DASHBOARD_CACHE_TIMEOUT = 10  # 10 seconds. keeps the dashboard snappy while avoiding appearing stale.


class DashboardView(SmarterAuthenticatedNeverCachedWebView):
    """
    Authenticated, per-user cached view that renders the React dashboard page.

    Extends :class:`~smarter.lib.django.views.SmarterAuthenticatedWebView`.
    Two decorators are applied at dispatch time:

    On a ``GET`` request the view redirects unauthenticated users to the login
    page, otherwise it builds a context dictionary containing API URLs for the
    "My Resources" and "Service Health" React widgets, then renders
    ``react/dashboard.html``.

    Attributes:
        template_path (str): Set at request time to ``"react/dashboard.html"``.
    """

    # template_path = "dashboard/authenticated.html"
    template_path = "react/dashboard.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this view."""
        class_name = f"{__name__}.{DashboardView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the dashboard page for authenticated users.

        :param request: The incoming HTTP GET request from the client.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments forwarded by the URL dispatcher.
        :param kwargs: Additional keyword arguments forwarded by the URL dispatcher.
        :returns: An HTTP response with the rendered dashboard page for authenticated users, or a redirect to the login page for unauthenticated users.
        :rtype: django.http.HttpResponse or django.http.HttpResponseRedirect
        """

        if not is_authenticated_request(request):
            return redirect(reverse("login_view"))

        # pylint: disable=C0415
        from smarter.apps.dashboard.views.views.api.urls import (
            DashboardApiReverseNames,
        )
        from smarter.apps.dashboard.views.views.urls import (
            DashboardReverseNames,  # avoid circular import
        )

        context = {
            "react_dashboard": {
                "root_id": "smarter-dashboard-root",
                "csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "my_resources_api_url": reverse(
                    DashboardReverseNames.namespace,
                    DashboardApiReverseNames.namespace,
                    DashboardApiReverseNames.my_resources,
                ),
                "service_health_api_url": reverse(
                    DashboardReverseNames.namespace,
                    DashboardApiReverseNames.namespace,
                    DashboardApiReverseNames.service_health,
                ),
                "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
                "smarter_request_id": self.smarter_request_id(),
            }
        }
        self.template_path = "react/dashboard.html"

        logger.debug(
            "%s.get() Rendering dashboard with context: %s", self.formatted_class_name, logging.formatted_json(context)
        )
        return render(request, self.template_path, context=context)
