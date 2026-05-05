"""
Django URL patterns for the chatapp

how we got here:
 - /providers/api/v1/

"""

from django.urls import path

from smarter.common.utils import camel_case_object_name

from .const import namespace
from .views.provider import ProviderDetailView, ProviderListView

app_name = namespace


class ProviderReverseViews:
    """
    Reverse view names for the Provider app.
    """

    namespace = namespace
    listview = camel_case_object_name(ProviderListView)
    detailview = camel_case_object_name(ProviderDetailView)


urlpatterns = [
    path("providers/", ProviderListView.as_view(), name=ProviderReverseViews.listview),
    path("providers/<str:name>/", ProviderDetailView.as_view(), name="provider_by_name"),
]
