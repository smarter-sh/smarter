"""
URL configuration of the doodle api.

These are mounted at ``/api/v1/doodles/``. See :mod:`smarter.apps.doodle.api.v1.views`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views import DoodleArtworkView, DoodleTodayView

app_name = namespace


class DoodleApiV1ReverseViews:
    """
    Reverse view names for the doodle api.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(f"{DoodleApiV1ReverseViews.namespace}:{DoodleApiV1ReverseViews.today}")
    """

    namespace = "api:v1:doodle"

    today = to_snake_case(DoodleTodayView.__name__)
    artwork = to_snake_case(DoodleArtworkView.__name__)


urlpatterns = [
    path("today/", DoodleTodayView.as_view(), name=DoodleApiV1ReverseViews.today),
    path("artwork/<str:sha256>.svg", DoodleArtworkView.as_view(), name=DoodleApiV1ReverseViews.artwork),
]
