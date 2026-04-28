"""URL configuration for the plugin app."""

from django.urls import path

from .const import namespace
from .views.plugin import PluginDetailView, PluginListView

app_name = namespace

urlpatterns = [
    path("plugins/", PluginListView.as_view(), name="plugin_listview"),
    path("plugins/<str:kind>/<str:name>/", PluginDetailView.as_view(), name="plugin_by_name"),
]
