"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.dashboard.views.dashboard.api.my_resources import MyResourcesView
from smarter.apps.dashboard.views.dashboard.api.service_health import ServiceHealthView
from smarter.common.utils import camel_case_object_name
from smarter.lib import logging

from .const import namespace

logger = logging.getLogger(__name__)

app_name = namespace


class DashboardApiReverseNames:
    """
    A class to hold the names of the dashboard views for easy reference throughout the codebase.
    """

    namespace = namespace

    my_resources = camel_case_object_name(MyResourcesView)
    service_health = camel_case_object_name(ServiceHealthView)


urlpatterns = [
    path("my-resources/", MyResourcesView.as_view(), name=DashboardApiReverseNames.my_resources),
    path("service-health/", ServiceHealthView.as_view(), name=DashboardApiReverseNames.service_health),
]
