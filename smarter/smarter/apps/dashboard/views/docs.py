# -*- coding: utf-8 -*-
"""Django docs views"""
import logging

from smarter.smarter.common.view_helpers import SmarterWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class GettingStartedView(SmarterWebView):
    """Top level legal view"""

    template_path = "dashboard/docs/getting-started.html"
