# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from smarter.view_helpers import SmarterAuthenticatedWebView


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class CustomAPIView(SmarterAuthenticatedWebView):
    """Custom API view for the API admin app."""

    template_path = "rest_framework/root_page_template.html"
