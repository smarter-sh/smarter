"""
URL configuration for the Guardrail app's endpoints in the web console's api.

These are mounted at ``/api/web/guardrail/``, and the Guardrail list page's React app calls
them. See :mod:`smarter.apps.api.web` and :mod:`smarter.apps.guardrail.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.guardrail.const import namespace
from smarter.apps.guardrail.views.listview.api import (
    GuardrailListApiCloneView,
    GuardrailListApiDeleteView,
    GuardrailListApiRenameView,
    GuardrailListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class GuardrailApiWebReverseNames:
    """
    Reverse view names for the Guardrail app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(GuardrailApiWebReverseNames.namespace, GuardrailApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(GuardrailListApiView.__name__)
    listview_all = to_snake_case(GuardrailListApiView.__name__) + "_all"
    clone = to_snake_case(GuardrailListApiCloneView.__name__)
    delete = to_snake_case(GuardrailListApiDeleteView.__name__)
    rename = to_snake_case(GuardrailListApiRenameView.__name__)


urlpatterns = [
    path("listview/", GuardrailListApiView.as_view(), name=GuardrailApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        GuardrailListApiView.as_view(),
        name=GuardrailApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:guardrail_id>/<str:new_name>/",
        GuardrailListApiCloneView.as_view(),
        name=GuardrailApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:guardrail_id>/",
        GuardrailListApiDeleteView.as_view(),
        name=GuardrailApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:guardrail_id>/<str:new_name>/",
        GuardrailListApiRenameView.as_view(),
        name=GuardrailApiWebReverseNames.rename,
    ),
]
