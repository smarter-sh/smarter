# pylint: disable=W0613
"""
smarter.apps.plugin.views.plugin
This module contains views to implement the card-style list view
in the Smarter Dashboard.
"""

import logging

from django.core.handlers.wsgi import WSGIRequest

from smarter.apps.plugin.models import PluginMeta
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView


logger = logging.getLogger(__name__)


class PluginDetailView(SmarterAuthenticatedNeverCachedWebView):
    """
    detail view for Smarter dashboard.
    """

    template_path = "plugin/plugin_detail.html"
    name: str = None
    kind: str = None
    plugin: PluginMeta = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.name = kwargs.pop("name", None)
        self.kind = kwargs.pop("kind", None)
        self.plugin = PluginMeta.get_cached_plugin_by_name(user=self.user, name=self.name)

    def get(self, request, *args, **kwargs):
        if not self.plugin:
            return SmarterHttpResponseNotFound(request=request, error_message="plugin not found")
        context = {}
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)


class PluginListView(SmarterAuthenticatedNeverCachedWebView):
    """
    list view for smarter workbench web console. It generates cards for each
    plugin.
    """

    template_path = "plugin/plugin_list.html"
    plugins: list[PluginMeta]

    def get(self, request: WSGIRequest, *args, **kwargs):
        self.plugins = PluginMeta.get_cached_plugins_for_user(self.user)
        context = {
            "plugins": self.plugins,
        }
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)
