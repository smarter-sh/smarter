# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from smarter.view_helpers import SmarterAPIAdminView


class CustomAPIView(SmarterAPIAdminView):
    """Custom API view for the API admin app."""

    template_path = "dashboard-default.html"
