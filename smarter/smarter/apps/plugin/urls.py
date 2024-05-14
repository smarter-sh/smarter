"""URL configuration for the plugin app."""

from django.urls import path

from .views.plugin import PluginsView, PluginView


urlpatterns = [
    path("", PluginsView.as_view(), name="plugins"),
    path("<int:plugin_id>", PluginView.as_view(), name="plugin"),
]
