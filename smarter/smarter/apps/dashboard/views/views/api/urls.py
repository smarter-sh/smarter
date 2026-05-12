"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.dashboard.views.views.api.my_resources import MyResourcesView
from smarter.apps.dashboard.views.views.api.service_health import ServiceHealthView
from smarter.common.utils import to_snake_case
from smarter.lib import logging

from .const import namespace

logger = logging.getLogger(__name__)

app_name = namespace


class DashboardApiReverseNames:
    """
    A class to hold the names of the dashboard views for easy reference throughout the codebase.
    """

    namespace = namespace

    my_resources = to_snake_case(MyResourcesView)
    service_health = to_snake_case(ServiceHealthView)


urlpatterns = [
    path("my-resources/", MyResourcesView.as_view(), name=DashboardApiReverseNames.my_resources),
    path("service-health/", ServiceHealthView.as_view(), name=DashboardApiReverseNames.service_health),
]
