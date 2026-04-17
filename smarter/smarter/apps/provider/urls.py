"""
Django URL patterns for the chatapp

how we got here:
 - /providers/api/v1/

"""

from django.urls import path

from .const import namespace
from .views.provider import ProviderDetailView, ProviderListView

app_name = namespace

urlpatterns = [
    path("providers/", ProviderListView.as_view(), name="provider_listview"),
    path("providers/<str:name>/", ProviderDetailView.as_view(), name="provider_by_name"),
]
