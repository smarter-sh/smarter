# -*- coding: utf-8 -*-
"""Django docs views"""
import logging

from smarter.view_helpers import SmarterAuthenticatedWebView


logger = logging.getLogger(__name__)


class GettingStartedView(SmarterAuthenticatedWebView):
    """Top level legal view"""

    template_path = "dashboard/docs/getting-started.html"
