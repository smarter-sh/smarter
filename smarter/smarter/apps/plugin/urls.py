"""URL configuration for the plugin app."""

from django.urls import path

from .const import namespace
from .views.connection import ConnectionDetailView, ConnectionListView
from .views.plugin import PluginDetailView, PluginsListView


app_name = namespace

urlpatterns = [
    path("plugins/", PluginsListView.as_view(), name="plugins_listview"),
    path("plugins/<str:name>/", PluginDetailView.as_view(), name="plugin_detail"),
    path("connections/", ConnectionListView.as_view(), name="connections_listview"),
    path("connections/<str:kind>/<str:name>/", ConnectionDetailView.as_view(), name="connection_detail"),
]
