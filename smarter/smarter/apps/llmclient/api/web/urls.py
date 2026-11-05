"""
URL configuration for the LLMClient app's endpoints in the web console's api.

These are mounted at ``/api/web/llmclient/``, and the Custom Domains list page's React app calls
them, under ``custom-domains/``. See :mod:`smarter.apps.api.web` and
:mod:`smarter.apps.llmclient.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.llmclient.const import namespace
from smarter.apps.llmclient.views.listview.api import (
    CustomDomainListApiCloneView,
    CustomDomainListApiDeleteView,
    CustomDomainListApiRenameView,
    CustomDomainListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class LLMClientApiWebReverseNames:
    """
    Reverse view names for the LLMClient app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(LLMClientApiWebReverseNames.namespace, LLMClientApiWebReverseNames.custom_domain_listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    custom_domain_listview = to_snake_case(CustomDomainListApiView.__name__)
    custom_domain_listview_all = to_snake_case(CustomDomainListApiView.__name__) + "_all"
    custom_domain_clone = to_snake_case(CustomDomainListApiCloneView.__name__)
    custom_domain_delete = to_snake_case(CustomDomainListApiDeleteView.__name__)
    custom_domain_rename = to_snake_case(CustomDomainListApiRenameView.__name__)


urlpatterns = [
    path(
        "custom-domains/listview/",
        CustomDomainListApiView.as_view(),
        name=LLMClientApiWebReverseNames.custom_domain_listview_all,
    ),
    re_path(
        r"^custom-domains/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        CustomDomainListApiView.as_view(),
        name=LLMClientApiWebReverseNames.custom_domain_listview,
    ),
    path(
        "custom-domains/clone/<int:custom_domain_id>/<str:new_name>/",
        CustomDomainListApiCloneView.as_view(),
        name=LLMClientApiWebReverseNames.custom_domain_clone,
    ),
    path(
        "custom-domains/delete/<int:custom_domain_id>/",
        CustomDomainListApiDeleteView.as_view(),
        name=LLMClientApiWebReverseNames.custom_domain_delete,
    ),
    path(
        "custom-domains/rename/<int:custom_domain_id>/<str:new_name>/",
        CustomDomainListApiRenameView.as_view(),
        name=LLMClientApiWebReverseNames.custom_domain_rename,
    ),
]
