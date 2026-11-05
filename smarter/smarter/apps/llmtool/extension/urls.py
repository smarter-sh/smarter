"""
URL patterns of the web console's Extensions pages: superusers manage extensions, others see them read-only.

The endpoints that the pages' React app calls are in the web console's api: see
:mod:`smarter.apps.llmtool.extension.api.web.urls`.

how we got here:
 - /extensions/
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .views import ExtensionDetailView, ExtensionListView

namespace = "extension"
app_name = namespace


class ExtensionReverseNames:
    """
    Named URL patterns of the Extensions pages.

    The pages' endpoints are in
    :class:`smarter.apps.llmtool.extension.api.web.urls.ExtensionApiWebReverseNames`.
    """

    namespace = namespace

    listview = to_snake_case(ExtensionListView.__name__)
    detailview = to_snake_case(ExtensionDetailView.__name__)


urlpatterns = [
    path("", ExtensionListView.as_view(), name=ExtensionReverseNames.listview),
    path("<slug:slug>/", ExtensionDetailView.as_view(), name=ExtensionReverseNames.detailview),
]
