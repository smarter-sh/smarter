"""
URL configuration for the Guardrail app API.

These are mounted at ``/api/v1/guardrails/``. See :mod:`smarter.apps.guardrail.api.v1.views.views`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.views import (
    GuardrailEvaluateView,
    GuardrailEventsView,
    GuardrailListView,
    GuardrailView,
)

app_name = namespace
BY_ID = "_by_id"
BY_HASHED_ID = "_by_hashed_id"


class GuardrailApiV1ReverseViews:
    """
    Reverse view names for the Guardrail api.

    Each Guardrail view is available by the Guardrail's hashed id, and by its id.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(
            f"{GuardrailApiV1ReverseViews.namespace}:{GuardrailApiV1ReverseViews.evaluate_by_hashed_id}",
            kwargs={"hashed_id": guardrail.hashed_id},
        )
    """

    namespace = "api:v1:guardrail"

    list_view = to_snake_case(GuardrailListView.__name__)

    guardrail_by_hashed_id = to_snake_case(GuardrailView.__name__) + BY_HASHED_ID
    evaluate_by_hashed_id = to_snake_case(GuardrailEvaluateView.__name__) + BY_HASHED_ID
    events_by_hashed_id = to_snake_case(GuardrailEventsView.__name__) + BY_HASHED_ID

    guardrail_by_id = to_snake_case(GuardrailView.__name__) + BY_ID
    evaluate_by_id = to_snake_case(GuardrailEvaluateView.__name__) + BY_ID
    events_by_id = to_snake_case(GuardrailEventsView.__name__) + BY_ID


urlpatterns = [
    path("", GuardrailListView.as_view(), name=GuardrailApiV1ReverseViews.list_view),
    # by guardrail_id
    path("<int:guardrail_id>/", GuardrailView.as_view(), name=GuardrailApiV1ReverseViews.guardrail_by_id),
    path(
        "<int:guardrail_id>/evaluate/", GuardrailEvaluateView.as_view(), name=GuardrailApiV1ReverseViews.evaluate_by_id
    ),
    path("<int:guardrail_id>/events/", GuardrailEventsView.as_view(), name=GuardrailApiV1ReverseViews.events_by_id),
    # by hashed_id
    path("<str:hashed_id>/", GuardrailView.as_view(), name=GuardrailApiV1ReverseViews.guardrail_by_hashed_id),
    path(
        "<str:hashed_id>/evaluate/",
        GuardrailEvaluateView.as_view(),
        name=GuardrailApiV1ReverseViews.evaluate_by_hashed_id,
    ),
    path("<str:hashed_id>/events/", GuardrailEventsView.as_view(), name=GuardrailApiV1ReverseViews.events_by_hashed_id),
]
