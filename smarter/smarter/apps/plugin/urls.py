"""URL configuration for the plugin app."""

from django.urls import path

from .const import namespace
from .views.connection import ConnectionDetailView, ConnectionListView
from .views.plugin import PluginDetailView, PluginListView


app_name = namespace

urlpatterns = [
    path("plugins/", PluginListView.as_view(), name="plugin_listview"),
    path("plugins/<str:name>/", PluginDetailView.as_view(), name="plugin_detail"),
    path("connections/", ConnectionListView.as_view(), name="connection_listview"),
    path("connections/<str:kind>/<str:name>/", ConnectionDetailView.as_view(), name="connection_detail"),
]
