"""
Django URL patterns for the provider app's web console pages.

- ``/provider/``
- ``/provider/providers/<hashed_id>/``

The Provider api is at ``/api/v1/providers/`` (:mod:`smarter.apps.provider.api.v1.urls`), and the
endpoints that the console's React apps call are at ``/api/web/provider/``
(:mod:`smarter.apps.provider.api.web.urls`).
"""

from django.urls import path

from smarter.apps.provider.views.detailview import ProviderDetailView
from smarter.apps.provider.views.listview.view import ProviderListView
from smarter.common.utils import to_snake_case

from .const import namespace

app_name = namespace


class ProviderReverseNames:
    """
    Reverse view names for the Provider app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.provider.api.web.urls.ProviderApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(ProviderDetailView.__name__)
    listview = to_snake_case(ProviderListView.__name__)


urlpatterns = [
    path("providers/<str:hashed_id>/", ProviderDetailView.as_view(), name=ProviderReverseNames.detailview),
    path("", ProviderListView.as_view(), name=ProviderReverseNames.listview),
]
