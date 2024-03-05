# -*- coding: utf-8 -*-
"""Django views"""
import logging

from smarter.view_helpers import SmarterAuthenticatedWebView, SmarterWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class DashboardView(SmarterWebView):
    """Public Access Dashboard view"""

    template_path = "landing-page.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.template_path = "dashboard/authenticated.html"
        return super().get(request, *args, **kwargs)


class DocumentationView(SmarterWebView):
    """Documentation view"""

    template_path = "dashboard/documentation.html"


class PlatformHelpView(SmarterWebView):
    """Platform help view"""

    template_path = "dashboard/help.html"


class ChangeLogView(SmarterWebView):
    """Notifications view"""

    template_path = "dashboard/changelog.html"


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class NotificationsView(SmarterAuthenticatedWebView):
    """Notifications view"""

    template_path = "dashboard/notifications.html"
