"""URL configuration for the connection app."""

from django.urls import path

from .const import namespace
from .views.connection import ConnectionDetailView, ConnectionListView

app_name = namespace

urlpatterns = [
    path("connections/", ConnectionListView.as_view(), name="connection_listview"),
    path("connections/<str:kind>/<str:name>/", ConnectionDetailView.as_view(), name="connection_by_name"),
]
