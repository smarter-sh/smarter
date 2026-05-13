"""
Django URL patterns for the chatapp

how we got here:
 - /providers/api/v1/

"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.provider import ProviderDetailView, ProviderListView

app_name = namespace


class ProviderReverseNames:
    """
    Reverse view names for the Provider app.
    """

    namespace = namespace
    listview = to_snake_case(ProviderListView)
    detailview = to_snake_case(ProviderDetailView)


urlpatterns = [
    path("providers/", ProviderListView.as_view(), name=ProviderReverseNames.listview),
    path("providers/<str:name>/", ProviderDetailView.as_view(), name="provider_by_name"),
]
