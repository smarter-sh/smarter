# -*- coding: utf-8 -*-
"""Plugin urls."""
from django.urls import path
from django.views.decorators.http import require_http_methods

from smarter.apps.plugin.views import plugin_clone_view, plugins_list_view, plugins_view


urlpatterns = [
    path("plugins/", require_http_methods(["POST"])(plugins_view), name="plugins_view"),
    path(
        "plugins/<int:plugin_id>/",
        require_http_methods(["GET", "POST", "PATCH", "DELETE"])(plugins_view),
        name="plugins_view",
    ),
    path(
        "plugins/<int:plugin_id>/clone/<str:new_name>",
        require_http_methods(["GET", "POST"])(plugin_clone_view),
        name="plugin_clone_view",
    ),
    path("plugins/", require_http_methods(["GET"])(plugins_list_view), name="plugins_list_view"),
]
