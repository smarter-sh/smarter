"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.secret.views.detailview import SecretDetailView
from smarter.apps.secret.views.listview.view import SecretListView
from smarter.common.utils import to_snake_case

from .const import namespace


class SecretReverseNames:
    """
    Reverse view names for the Secret app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.secret.api.web.urls.SecretApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(SecretDetailView.__name__)
    listview = to_snake_case(SecretListView.__name__)


app_name = namespace

urlpatterns = [
    path("", SecretListView.as_view(), name=SecretReverseNames.listview),
    path("secrets/<str:hashed_id>/", SecretDetailView.as_view(), name=SecretReverseNames.detailview),
]
