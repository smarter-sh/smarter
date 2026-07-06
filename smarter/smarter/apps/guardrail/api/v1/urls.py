"""URL configuration for guardrail app."""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.default import DefaultGuardrailApiView
from .views.views import (
    GuardrailListView,
    GuardrailView,
)

app_name = namespace
BY_ID = "by_id"
BY_HASHED_ID = "by_hashed_id"


class GuardrailApiV1ReverseViews:
    """
    Reverse views for the Guardrail CLI commands.

    Provides named references for reversing CLI-related API endpoints.

    This class is used for reverse URL resolution in Django, where each attribute
    corresponds to a CLI command endpoint. The names are derived from the actual
    API view class names, ensuring consistency and reducing the risk of typos
    when using Django's URL reversing features.

    All CLI commands available in the Smarter platform are included as attributes
    of this class. This centralizes the reverse URL names for all CLI endpoints,
    making it easier to maintain and reference them throughout the codebase.

    Usage
    -----
    Use these attributes with Django's ``reverse()`` function or in templates
    to generate URLs for CLI API endpoints based on the view class names.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse
        url = reverse(ApiV1CliReverseViews.deploy, kwargs={'kind': 'Plugin'})

        str(ApiV1CliReverseViews.deploy)
        returns 'api_v1_cli_deploy_api_view'
    """

    namespace = f"api:{namespace}:guardrail"

    # reverse() by hashed_id
    # --------------------------------------------------------------------------
    guardrail_view_by_hashed_id = to_snake_case(GuardrailView.__name__) + BY_HASHED_ID
    default_guardrail_api_view_by_hashed_id = to_snake_case(DefaultGuardrailApiView.__name__) + BY_HASHED_ID

    # legacy reverse() references by guardrail_id
    # --------------------------------------------------------------------------
    default_guardrail_api_view_by_id = to_snake_case(DefaultGuardrailApiView.__name__)

    # currently no reverse() references to these named views.
    # --------------------------------------------------------------------------
    guardrail_list_view = to_snake_case(GuardrailListView.__name__)
    guardrail_view_by_id = to_snake_case(GuardrailView.__name__) + BY_ID


urlpatterns = [
    path("", GuardrailListView.as_view(), name=GuardrailApiV1ReverseViews.guardrail_list_view),
    # --------------------------------------------------------------------------
    # paths by hashed_id
    # --------------------------------------------------------------------------
    path("<str:hashed_id>/", GuardrailView.as_view(), name=GuardrailApiV1ReverseViews.guardrail_view_by_hashed_id),
    path(
        "<str:hashed_id>/guardrail/",
        DefaultGuardrailApiView.as_view(),
        name=GuardrailApiV1ReverseViews.default_guardrail_api_view_by_hashed_id,
    ),
    # --------------------------------------------------------------------------
    # paths by guardrail_id
    # --------------------------------------------------------------------------
    path("<int:guardrail_id>/", GuardrailView.as_view(), name=GuardrailApiV1ReverseViews.guardrail_view_by_id),
    path(
        "<int:guardrail_id>/guardrail/",
        DefaultGuardrailApiView.as_view(),
        name=GuardrailApiV1ReverseViews.default_guardrail_api_view_by_id,
    ),
]
