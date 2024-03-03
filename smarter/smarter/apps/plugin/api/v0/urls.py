# -*- coding: utf-8 -*-
"""Plugin urls."""
from django.urls import path

from .views import PluginCloneView, PluginsListView, PluginView


urlpatterns = [
    path("", PluginsListView.as_view(), name="plugins_list_view"),
    path(
        "<int:plugin_id>/",
        PluginView.as_view(),
        name="plugin_view",
    ),
    path(
        "<int:plugin_id>/clone/<str:new_name>",
        PluginCloneView.as_view(),
        name="plugin_clone_view",
    ),
]
