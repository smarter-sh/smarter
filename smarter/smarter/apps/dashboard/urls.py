"""URL configuration for the web platform."""

from django.urls import include, path

from smarter.apps.dashboard.const import namespace
from smarter.apps.dashboard.views.dashboard import urls as dashboard_urls
from smarter.apps.dashboard.views.logs import urls as logs_urls
from smarter.apps.dashboard.views.passthrough import urls as passthrough_urls
from smarter.apps.dashboard.views.profile import urls as profile_urls
from smarter.lib import logging

logger = logging.getLogger(__name__)

app_name = namespace


urlpatterns = [
    path("", include(dashboard_urls)),
    path("logs/", include(logs_urls, namespace=logs_urls.app_name)),
    path("passthrough/", include(passthrough_urls, namespace=passthrough_urls.app_name)),
    path("profile/", include(profile_urls, namespace=profile_urls.app_name)),
]
