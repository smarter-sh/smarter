# -*- coding: utf-8 -*-
"""Django views"""
import logging

from smarter.view_helpers import SmarterAuthenticatedCachedWebView


logger = logging.getLogger(__name__)


class DashboardView(SmarterAuthenticatedCachedWebView):
    """Dashboard view"""

    template_path = "dashboard/dashboard.html"


class APIKeysView(SmarterAuthenticatedCachedWebView):
    """API keys view"""

    template_path = "dashboard/api-keys.html"


class PluginsView(SmarterAuthenticatedCachedWebView):
    """Plugins view"""

    template_path = "dashboard/plugins.html"


class UsageView(SmarterAuthenticatedCachedWebView):
    """Usage view"""

    template_path = "dashboard/usage.html"


class DocumentationView(SmarterAuthenticatedCachedWebView):
    """Documentation view"""

    template_path = "dashboard/documentation.html"


class PlatformHelpView(SmarterAuthenticatedCachedWebView):
    """Platform help view"""

    template_path = "dashboard/help.html"


class NotificationsView(SmarterAuthenticatedCachedWebView):
    """Notifications view"""

    template_path = "dashboard/notifications.html"
