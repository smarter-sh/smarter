# pylint: disable=W0613
"""Django views"""

from django.conf import settings
from django.http.request import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control

from smarter.common.utils import is_authenticated_request
from smarter.lib import logging
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
    smarter_cache_page_by_user,
)

logger = logging.getLogger(__name__)
DASHBOARD_CACHE_TIMEOUT = 10  # 10 seconds. keeps the dashboard snappy while avoiding appearing stale.


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
@method_decorator(cache_control(max_age=DASHBOARD_CACHE_TIMEOUT), name="dispatch")
@method_decorator(smarter_cache_page_by_user(DASHBOARD_CACHE_TIMEOUT), name="dispatch")
class DashboardView(SmarterAuthenticatedWebView):
    """Public Access Dashboard view"""

    # template_path = "dashboard/authenticated.html"
    template_path = "react/dashboard.html"

    def get(self, request: HttpRequest, *args, **kwargs):

        if not is_authenticated_request(request):
            return redirect(reverse("login_view"))

        # pylint: disable=C0415
        from smarter.apps.dashboard.urls import DashboardNames  # avoid circular import

        context = {
            "dashboard": {
                "root_id": "smarter-dashboard-root",
                "csrf_cookie_name": settings.CSRF_COOKIE_NAME,  # this is the CSRF token cookie that should be included in the header of the POST request from the frontend.
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,  # this is the Django session.
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "my_resources_api_url": reverse(":".join([DashboardNames.namespace, DashboardNames.api_my_resources])),
                "service_health_api_url": reverse(
                    ":".join([DashboardNames.namespace, DashboardNames.api_service_health])
                ),
            }
        }
        self.template_path = "react/dashboard.html"

        logger.debug("%s.get() Rendering dashboard with context: %s", self.formatted_class_name, context)
        return render(request, self.template_path, context=context)
