"""URL configuration for the web platform."""

from django.urls import include, path
from django.views.generic.base import RedirectView

from smarter.apps.account import urls as account_urls
from smarter.apps.dashboard import urls_profile
from smarter.apps.plugin import urls as plugin_urls
from smarter.common.conf import smarter_settings
from smarter.common.utils import camel_case_object_name
from smarter.lib import logging

from .const import namespace
from .views.dashboard import ChangeLogView, DashboardView, EmailAdded, NotificationsView
from .views.dashboard.api.my_resources import MyResourcesView
from .views.dashboard.api.service_health import ServiceHealthView
from .views.logs import urls as logs_urls
from .views.manifest_drop_zone import ManifestDropZoneView

logger = logging.getLogger(__name__)

app_name = namespace


class DashboardNames:
    """
    A class to hold the names of the dashboard views for easy reference throughout the codebase.
    """

    namespace = namespace

    dashboard = namespace
    notifications = camel_case_object_name(NotificationsView)
    changelog = camel_case_object_name(ChangeLogView)
    email_added = camel_case_object_name(EmailAdded)
    manifest_drop_zone = camel_case_object_name(ManifestDropZoneView)
    api_my_resources = camel_case_object_name(MyResourcesView)
    api_service_health = camel_case_object_name(ServiceHealthView)


urlpatterns = [
    path("", DashboardView.as_view(), name=DashboardNames.dashboard),
    path("api/my-resources/", MyResourcesView.as_view(), name=DashboardNames.api_my_resources),
    path("api/service-health/", ServiceHealthView.as_view(), name=DashboardNames.api_service_health),
    path("logs/", include(logs_urls, namespace=logs_urls.app_name)),
    path("account/", include(account_urls)),
    path("plugins/", include(plugin_urls)),
    path("profile/", include(urls_profile)),
    path("help/", RedirectView.as_view(url="/docs/"), name="help"),
    path("support/", RedirectView.as_view(url="/docs/"), name="support"),
    path("changelog/", ChangeLogView.as_view(), name=DashboardNames.changelog),
    path("notifications/", NotificationsView.as_view(), name=DashboardNames.notifications),
    path("email-added/", EmailAdded.as_view(), name=DashboardNames.email_added),
]

if smarter_settings.enable_dashboard_passthrough_prompt:
    from .urls_passthrough import urlpatterns as passthrough_urlpatterns

    urlpatterns += passthrough_urlpatterns
    logger.info(
        "%s Dashboard prompt passthrough endpoint enabled.",
        logging.formatted_text(__name__),
    )
else:
    logger.info(
        "%s Dashboard prompt passthrough endpoint is disabled. Set env `SMARTER_ENABLE_DASHBOARD_PASSTHROUGH_PROMPT=true` to enable the LLM prompt API passthrough request/response endpoint at /prompt/.",
        logging.formatted_text(__name__),
    )

if smarter_settings.enable_dashboard_apply:
    urlpatterns.append(
        path("apply/", ManifestDropZoneView.as_view(), name=DashboardNames.manifest_drop_zone),
    )
    logger.info(
        "%s Dashboard apply drop zone endpoint enabled. This allows users to apply manifests by dragging and dropping files onto the dashboard. Set env `SMARTER_ENABLE_DASHBOARD_APPLY=false` to disable.",
        logging.formatted_text(__name__),
    )
else:
    logger.info(
        "%s Dashboard apply drop zone endpoint is disabled. Set env `SMARTER_ENABLE_DASHBOARD_APPLY=true` to enable the manifest drop zone at /apply/.",
        logging.formatted_text(__name__),
    )
