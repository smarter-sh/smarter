# -*- coding: utf-8 -*-
"""Django views"""
from smarter.view_helpers import SmarterAuthenticatedWebView


class ChatAppView(SmarterAuthenticatedWebView):
    """Chat app view for smarter web."""

    template_path = "index.html"
