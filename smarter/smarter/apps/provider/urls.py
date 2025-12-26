"""
Django URL patterns for the chatapp

how we got here:
 - /providers/api/v1/

"""

from django.urls import include, path

from .api.const import namespace as api_namespace
from .const import namespace
from .views.provider import ProviderDetailView, ProviderListView


app_name = namespace

urlpatterns = [
    path("api/", include("smarter.apps.provider.api.urls", namespace=api_namespace)),
    path("providers/", ProviderListView.as_view(), name="provider_listview"),
    path("providers/<str:name>/", ProviderDetailView.as_view(), name="provider_by_name"),
]
