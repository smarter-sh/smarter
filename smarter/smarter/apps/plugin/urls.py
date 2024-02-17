# -*- coding: utf-8 -*-
"""Plugin urls."""
from django.urls import path
from django.views.decorators.http import require_http_methods

from smarter.apps.plugin.views import plugin_create_view, plugin_view, plugins_view


urlpatterns = [
    path("plugins/create", require_http_methods(["GET", "POST"])(plugin_create_view), name="plugin_create_view"),
    path("plugins/<int:plugin_id>/", require_http_methods(["GET", "PATCH", "DELETE"])(plugin_view), name="plugin_view"),
    path("plugins/", require_http_methods(["GET"])(plugins_view), name="plugins_view"),
]
