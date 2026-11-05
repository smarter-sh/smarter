"""
Django URL patterns of the infrastructure app: the ledger of cloud resources.

how we got here:
 - /infrastructure/
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.listview import InfrastructureResourceListView

app_name = namespace


class InfrastructureReverseNames:
    """
    Named URL patterns of the infrastructure app's console pages.

    The endpoint that the list page's React app calls is in the web console's api:
    see :class:`smarter.apps.infrastructure.api.web.urls.InfrastructureApiWebReverseNames`.
    """

    namespace = namespace

    listview = to_snake_case(InfrastructureResourceListView.__name__)


urlpatterns = [
    path("", InfrastructureResourceListView.as_view(), name=InfrastructureReverseNames.listview),
]
