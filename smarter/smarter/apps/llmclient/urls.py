"""URL configuration for the llmclient app's web console views."""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.detailview import CustomDomainDetailView
from .views.listview.view import CustomDomainListView

app_name = namespace


class LLMClientReverseNames:
    """
    Reverse view names for the llmclient app's console pages.

    The endpoints that the Custom Domains list page's React app calls are in the web console's api:
    see :class:`smarter.apps.llmclient.api.web.urls.LLMClientApiWebReverseNames`.
    """

    namespace = namespace

    custom_domain_listview = to_snake_case(CustomDomainListView.__name__)
    custom_domain_detailview = to_snake_case(CustomDomainDetailView.__name__)


urlpatterns = [
    path("custom-domains/", CustomDomainListView.as_view(), name=LLMClientReverseNames.custom_domain_listview),
    path(
        "custom-domains/<str:hashed_id>/",
        CustomDomainDetailView.as_view(),
        name=LLMClientReverseNames.custom_domain_detailview,
    ),
]
