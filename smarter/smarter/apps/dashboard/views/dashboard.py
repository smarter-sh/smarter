# -*- coding: utf-8 -*-
"""Django views"""
import logging

from smarter.view_helpers import SmarterAuthenticatedWebView, SmarterWebView


logger = logging.getLogger(__name__)


class DashboardView(SmarterWebView):
    """Public Access Dashboard view"""

    template_path = "dashboard/dashboard.html"


class DocumentationView(SmarterAuthenticatedWebView):
    """Documentation view"""

    template_path = "dashboard/documentation.html"


class PlatformHelpView(SmarterAuthenticatedWebView):
    """Platform help view"""

    template_path = "dashboard/help.html"


class NotificationsView(SmarterAuthenticatedWebView):
    """Notifications view"""

    template_path = "dashboard/notifications.html"


class ChangeLogView(SmarterAuthenticatedWebView):
    """Notifications view"""

    template_path = "dashboard/changelog.html"
