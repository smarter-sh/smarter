"""URL configuration for the plugin app."""

from django.urls import path

from .const import namespace
from .views.plugin import PluginsView, PluginView


app_name = namespace

urlpatterns = [
    path("", PluginsView.as_view(), name="plugins_view"),
    path("<int:plugin_id>", PluginView.as_view(), name="plugin_view_by_id"),
]
