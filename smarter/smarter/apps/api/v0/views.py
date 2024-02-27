# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from django.shortcuts import render


def custom_api_root(request):
    return render(request, "rest_framework/root_page_template.html")
