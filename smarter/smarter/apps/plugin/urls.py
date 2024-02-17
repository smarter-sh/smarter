# -*- coding: utf-8 -*-
"""Plugin urls."""
from django.urls import path
from django.views.decorators.http import require_http_methods

from smarter.apps.plugin.views import plugin_create_view, plugin_view, plugins_view


urlpatterns = [
    path("create", require_http_methods(["POST"])(plugin_create_view), name="plugin_create_view"),
    path("<int:plugin_id>/", require_http_methods(["GET", "POST", "PATCH", "DELETE"])(plugin_view), name="plugin_view"),
    path("", require_http_methods(["GET"])(plugins_view), name="plugins_view"),
]
