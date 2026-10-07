"""
URL configuration for the LLMHost app API.

These are mounted at ``/api/v1/llmhosts/``. See :mod:`smarter.apps.llmhost.api.v1.views.views`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.views import (
    LLMHostDeployView,
    LLMHostDiscoverManifestView,
    LLMHostDiscoverView,
    LLMHostListView,
    LLMHostLogsView,
    LLMHostPlanView,
    LLMHostReportView,
    LLMHostStatusView,
    LLMHostUndeployView,
    LLMHostView,
)

app_name = namespace
BY_ID = "_by_id"
BY_HASHED_ID = "_by_hashed_id"

PER_LLMHOST = {
    "": LLMHostView,
    "status/": LLMHostStatusView,
    "logs/": LLMHostLogsView,
    "plan/": LLMHostPlanView,
    "deploy/": LLMHostDeployView,
    "undeploy/": LLMHostUndeployView,
}
"""The views of one LLMHost, by URL suffix."""


class LLMHostApiV1ReverseViews:
    """
    Reverse view names for the LLMHost api.

    Each LLMHost view is available by the LLMHost's hashed id, and by its id.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(
            f"{LLMHostApiV1ReverseViews.namespace}:{LLMHostApiV1ReverseViews.status_by_hashed_id}",
            kwargs={"hashed_id": llmhost.hashed_id},
        )
    """

    namespace = "api:v1:llmhost"

    list_view = to_snake_case(LLMHostListView.__name__)
    report = to_snake_case(LLMHostReportView.__name__)
    discover = to_snake_case(LLMHostDiscoverView.__name__)
    discover_manifest = to_snake_case(LLMHostDiscoverManifestView.__name__)

    llmhost_by_hashed_id = to_snake_case(LLMHostView.__name__) + BY_HASHED_ID
    status_by_hashed_id = to_snake_case(LLMHostStatusView.__name__) + BY_HASHED_ID
    logs_by_hashed_id = to_snake_case(LLMHostLogsView.__name__) + BY_HASHED_ID
    plan_by_hashed_id = to_snake_case(LLMHostPlanView.__name__) + BY_HASHED_ID
    deploy_by_hashed_id = to_snake_case(LLMHostDeployView.__name__) + BY_HASHED_ID
    undeploy_by_hashed_id = to_snake_case(LLMHostUndeployView.__name__) + BY_HASHED_ID

    llmhost_by_id = to_snake_case(LLMHostView.__name__) + BY_ID
    status_by_id = to_snake_case(LLMHostStatusView.__name__) + BY_ID
    logs_by_id = to_snake_case(LLMHostLogsView.__name__) + BY_ID
    plan_by_id = to_snake_case(LLMHostPlanView.__name__) + BY_ID
    deploy_by_id = to_snake_case(LLMHostDeployView.__name__) + BY_ID
    undeploy_by_id = to_snake_case(LLMHostUndeployView.__name__) + BY_ID


urlpatterns = [
    path("", LLMHostListView.as_view(), name=LLMHostApiV1ReverseViews.list_view),
    path("report/", LLMHostReportView.as_view(), name=LLMHostApiV1ReverseViews.report),
    path("discover/", LLMHostDiscoverView.as_view(), name=LLMHostApiV1ReverseViews.discover),
    path(
        "discover/manifest/",
        LLMHostDiscoverManifestView.as_view(),
        name=LLMHostApiV1ReverseViews.discover_manifest,
    ),
]
for suffix, view in PER_LLMHOST.items():
    view_name = to_snake_case(view.__name__)
    urlpatterns += [
        path(f"<int:llmhost_id>/{suffix}", view.as_view(), name=view_name + BY_ID),
        path(f"<str:hashed_id>/{suffix}", view.as_view(), name=view_name + BY_HASHED_ID),
    ]
