"""URL configuration for vectorsearch app."""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.default import DefaultVectorsearchApiView
from .views.views import (
    VectorsearchListView,
    VectorsearchView,
)

app_name = namespace
BY_ID = "by_id"
BY_HASHED_ID = "by_hashed_id"


class VectorsearchApiV1ReverseViews:
    """
    Reverse views for the Vectorsearch CLI commands.

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

    namespace = f"api:{namespace}:vectorsearch"

    # reverse() by hashed_id
    # --------------------------------------------------------------------------
    vectorsearch_view_by_hashed_id = to_snake_case(VectorsearchView.__name__) + BY_HASHED_ID
    default_vectorsearch_api_view_by_hashed_id = to_snake_case(DefaultVectorsearchApiView.__name__) + BY_HASHED_ID

    # legacy reverse() references by vectorsearch_id
    # --------------------------------------------------------------------------
    default_vectorsearch_api_view_by_id = to_snake_case(DefaultVectorsearchApiView.__name__)

    # currently no reverse() references to these named views.
    # --------------------------------------------------------------------------
    vectorsearch_list_view = to_snake_case(VectorsearchListView.__name__)
    vectorsearch_view_by_id = to_snake_case(VectorsearchView.__name__) + BY_ID


urlpatterns = [
    path("", VectorsearchListView.as_view(), name=VectorsearchApiV1ReverseViews.vectorsearch_list_view),
    # --------------------------------------------------------------------------
    # paths by hashed_id
    # --------------------------------------------------------------------------
    path(
        "<str:hashed_id>/",
        VectorsearchView.as_view(),
        name=VectorsearchApiV1ReverseViews.vectorsearch_view_by_hashed_id,
    ),
    path(
        "<str:hashed_id>/vectorsearch/",
        DefaultVectorsearchApiView.as_view(),
        name=VectorsearchApiV1ReverseViews.default_vectorsearch_api_view_by_hashed_id,
    ),
    # --------------------------------------------------------------------------
    # paths by vectorsearch_id
    # --------------------------------------------------------------------------
    path(
        "<int:vectorsearch_id>/", VectorsearchView.as_view(), name=VectorsearchApiV1ReverseViews.vectorsearch_view_by_id
    ),
    path(
        "<int:vectorsearch_id>/vectorsearch/",
        DefaultVectorsearchApiView.as_view(),
        name=VectorsearchApiV1ReverseViews.default_vectorsearch_api_view_by_id,
    ),
]
