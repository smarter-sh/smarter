# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from django.shortcuts import render

from smarter.view_helpers import SmarterAPIAdminView


def custom_api_root(request):
    return render(request, "rest_framework/root_page_template.html")


class CustomAPIView(SmarterAPIAdminView):
    """Custom API view for the API admin app."""

    template_path = "dashboard-default.html"
