# -*- coding: utf-8 -*-
"""Django views"""
from smarter.apps.common.view_helpers import SmarterAuthenticatedWebView


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class ChatAppView(SmarterAuthenticatedWebView):
    """Chat app view for smarter web."""

    template_path = "index.html"
