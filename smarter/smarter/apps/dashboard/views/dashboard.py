# -*- coding: utf-8 -*-
"""Django views"""
import logging

from smarter.view_helpers import SmarterWebView


logger = logging.getLogger(__name__)


class DashboardView(SmarterWebView):
    """Dashboard view"""

    def get(self, request):
        return self.cached_clean_http_response(request=request, template_path="dashboard/dashboard.html")


class APIKeysView(SmarterWebView):
    """API keys view"""

    def get(self, request):
        return self.cached_clean_http_response(request=request, template_path="dashboard/api-keys.html")


class PluginsView(SmarterWebView):
    """Plugins view"""

    def get(self, request):
        return self.cached_clean_http_response(request=request, template_path="dashboard/plugins.html")


class UsageView(SmarterWebView):
    """Usage view"""

    def get(self, request):
        return self.cached_clean_http_response(request=request, template_path="dashboard/usage.html")


class DocumentationView(SmarterWebView):
    """Documentation view"""

    def get(self, request):
        return self.cached_clean_http_response(request=request, template_path="dashboard/documentation.html")


class PlatformHelpView(SmarterWebView):
    """Platform help view"""

    def get(self, request):
        return self.cached_clean_http_response(request=request, template_path="dashboard/help.html")


class NotificationsView(SmarterWebView):
    """Notifications view"""

    def get(self, request):
        return self.cached_clean_http_response(request=request, template_path="dashboard/notifications.html")
