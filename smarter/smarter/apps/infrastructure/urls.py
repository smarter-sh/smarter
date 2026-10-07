"""
Django URL patterns of the infrastructure app: the ledger of cloud resources.

how we got here:
 - /infrastructure/
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.listview import (
    InfrastructureResourceListApiView,
    InfrastructureResourceListView,
)

app_name = namespace


class InfrastructureReverseNames:
    """Named URL patterns of the infrastructure app."""

    namespace = namespace

    listview = to_snake_case(InfrastructureResourceListView.__name__)
    listview_api = to_snake_case(InfrastructureResourceListApiView.__name__)


urlpatterns = [
    path("", InfrastructureResourceListView.as_view(), name=InfrastructureReverseNames.listview),
    path(
        "react-integration/api/listview/",
        InfrastructureResourceListApiView.as_view(),
        name=InfrastructureReverseNames.listview_api,
    ),
]
