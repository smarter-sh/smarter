"""URL configuration for the llmclient app's web console views."""

from django.urls import path, re_path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.detailview import CustomDomainDetailView
from .views.listview.api import (
    CustomDomainListApiCloneView,
    CustomDomainListApiDeleteView,
    CustomDomainListApiRenameView,
    CustomDomainListApiView,
)
from .views.listview.view import CustomDomainListView

app_name = namespace


class LLMClientReverseNames:
    """Reverse view names for the llmclient app."""

    namespace = namespace

    custom_domain_listview = to_snake_case(CustomDomainListView.__name__)
    custom_domain_detailview = to_snake_case(CustomDomainDetailView.__name__)
    custom_domain_listview_api = to_snake_case(CustomDomainListApiView.__name__)
    custom_domain_listview_api_all = to_snake_case(CustomDomainListApiView.__name__) + "_all"
    custom_domain_listview_api_clone = to_snake_case(CustomDomainListApiCloneView.__name__)
    custom_domain_listview_api_delete = to_snake_case(CustomDomainListApiDeleteView.__name__)
    custom_domain_listview_api_rename = to_snake_case(CustomDomainListApiRenameView.__name__)


urlpatterns = [
    path("custom-domains/", CustomDomainListView.as_view(), name=LLMClientReverseNames.custom_domain_listview),
    path(
        "custom-domains/react-integration/api/listview/",
        CustomDomainListApiView.as_view(),
        name=LLMClientReverseNames.custom_domain_listview_api_all,
    ),
    re_path(
        r"^custom-domains/react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        CustomDomainListApiView.as_view(),
        name=LLMClientReverseNames.custom_domain_listview_api,
    ),
    path(
        "custom-domains/react-integration/api/clone/<int:custom_domain_id>/<str:new_name>/",
        CustomDomainListApiCloneView.as_view(),
        name=LLMClientReverseNames.custom_domain_listview_api_clone,
    ),
    path(
        "custom-domains/react-integration/api/delete/<int:custom_domain_id>/",
        CustomDomainListApiDeleteView.as_view(),
        name=LLMClientReverseNames.custom_domain_listview_api_delete,
    ),
    path(
        "custom-domains/react-integration/api/rename/<int:custom_domain_id>/<str:new_name>/",
        CustomDomainListApiRenameView.as_view(),
        name=LLMClientReverseNames.custom_domain_listview_api_rename,
    ),
    path(
        "custom-domains/<str:hashed_id>/",
        CustomDomainDetailView.as_view(),
        name=LLMClientReverseNames.custom_domain_detailview,
    ),
]
