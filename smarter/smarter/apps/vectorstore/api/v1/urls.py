"""
URL configuration for the vectorstore API v1.
"""

from django.urls import path

from smarter.apps.vectorstore.api.v1.views import VectorstoreListView, VectorstoreView

from .const import namespace

app_name = namespace

urlpatterns = [
    path("", VectorstoreListView.as_view(), name="vectorstore_list_view"),
    path("<int:vectorstore_id>/", VectorstoreView.as_view(), name="vectorstore_view"),
]
