"""
Django URL patterns for the guardrail app's web console pages.

- ``/guardrail/``
- ``/guardrail/guardrails/<hashed_id>/``

The Guardrail api is at ``/api/v1/guardrails/`` (:mod:`smarter.apps.guardrail.api.v1.urls`), and the
endpoints that the console's React apps call are at ``/api/web/guardrail/``
(:mod:`smarter.apps.guardrail.api.web.urls`).
"""

from django.urls import path

from smarter.apps.guardrail.views.detailview import GuardrailDetailView
from smarter.apps.guardrail.views.listview.view import GuardrailListView
from smarter.common.utils import to_snake_case

from .const import namespace

app_name = namespace


class GuardrailReverseNames:
    """
    Reverse view names for the Guardrail app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.guardrail.api.web.urls.GuardrailApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(GuardrailDetailView.__name__)
    listview = to_snake_case(GuardrailListView.__name__)


urlpatterns = [
    path("guardrails/<str:hashed_id>/", GuardrailDetailView.as_view(), name=GuardrailReverseNames.detailview),
    path("", GuardrailListView.as_view(), name=GuardrailReverseNames.listview),
]
