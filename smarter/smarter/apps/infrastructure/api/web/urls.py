"""
URL configuration for the Infrastructure app's endpoints in the web console's api.

These are mounted at ``/api/web/infrastructure/``, and the Infrastructure Resource list page's
React app calls them. See :mod:`smarter.apps.api.web` and
:class:`smarter.apps.infrastructure.views.listview.InfrastructureResourceListApiView`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.infrastructure.const import namespace
from smarter.apps.infrastructure.views.listview import (
    InfrastructureResourceListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class InfrastructureApiWebReverseNames:
    """
    Reverse view names for the Infrastructure app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(InfrastructureApiWebReverseNames.namespace, InfrastructureApiWebReverseNames.listview)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(InfrastructureResourceListApiView.__name__)


urlpatterns = [
    path(
        "listview/",
        InfrastructureResourceListApiView.as_view(),
        name=InfrastructureApiWebReverseNames.listview,
    ),
]
