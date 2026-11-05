"""
Django URL patterns for the llmhost app's web console pages.

- ``/llmhost/``
- ``/llmhost/llmhosts/<hashed_id>/``
- ``/llmhost/compute/``
- ``/llmhost/compute/<hashed_id>/``

The LLMHost api is at ``/api/v1/llmhosts/`` (:mod:`smarter.apps.llmhost.api.v1.urls`), and the
endpoints that the console's React apps call are at ``/api/web/llmhost/``
(:mod:`smarter.apps.llmhost.api.web.urls`).
"""

from django.urls import path

from smarter.apps.llmhost.views.detailview import (
    LLMHostComputeDetailView,
    LLMHostDetailView,
)
from smarter.apps.llmhost.views.listview.view import (
    LLMHostComputeListView,
    LLMHostListView,
)
from smarter.common.utils import to_snake_case

from .const import namespace

app_name = namespace


class LLMHostReverseNames:
    """
    Reverse view names for the LLMHost app's console pages.

    The endpoints that the list pages' React apps call are in the web console's api:
    see :class:`smarter.apps.llmhost.api.web.urls.LLMHostApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(LLMHostDetailView.__name__)
    listview = to_snake_case(LLMHostListView.__name__)

    compute_detailview = to_snake_case(LLMHostComputeDetailView.__name__)
    compute_listview = to_snake_case(LLMHostComputeListView.__name__)


urlpatterns = [
    path("llmhosts/<str:hashed_id>/", LLMHostDetailView.as_view(), name=LLMHostReverseNames.detailview),
    path("", LLMHostListView.as_view(), name=LLMHostReverseNames.listview),
    path("compute/", LLMHostComputeListView.as_view(), name=LLMHostReverseNames.compute_listview),
    path(
        "compute/<str:hashed_id>/",
        LLMHostComputeDetailView.as_view(),
        name=LLMHostReverseNames.compute_detailview,
    ),
]
