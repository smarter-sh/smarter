# -*- coding: utf-8 -*-
"""Plugin views"""
import logging

from smarter.common.view_helpers import SmarterAuthenticatedWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class PluginView(SmarterAuthenticatedWebView):
    """Plugins view"""

    template_path = "plugin/plugin.html"

    # pylint: disable=unused-argument
    def get(self, request, *args, **kwargs):
        """Get request"""
        plugin_id = kwargs.get("plugin_id")
        logger.info("Plugin ID: %s", plugin_id)
        return self.clean_http_response(request, template_path=self.template_path)


class PluginsView(SmarterAuthenticatedWebView):
    """Plugins view"""

    template_path = "plugin/plugins.html"
