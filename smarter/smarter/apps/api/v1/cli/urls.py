"""
Smarter API command-line interface URL configuration.

- https://platform.smarter.sh/api/v1/cli/get/            # Return information about the  specified resource
- https://platform.smarter.sh/api/v1/cli/apply/          # Apply a manifest
- https://platform.smarter.sh/api/v1/cli/describe/       # print the manifest
- https://platform.smarter.sh/api/v1/cli/deploy/         # Deploy a resource
- https://platform.smarter.sh/api/v1/cli/logs/           # Get logs for a resource
- https://platform.smarter.sh/api/v1/cli/delete/         # Delete a resource
- https://platform.smarter.sh/api/v1/cli/status/         # Smarter platform status
- https://platform.smarter.sh/api/v1/cli/version/        # returns detailed version information on the platform
- https://platform.smarter.sh/api/v1/cli/whoami/         # Return information about the current IAM user
"""

from django.urls import path

from .views.apply import ApiV1CliApplyApiView
from .views.delete import ApiV1CliDeleteApiView
from .views.deploy import ApiV1CliDeployApiView
from .views.describe import ApiV1CliDescribeApiView
from .views.get import ApiV1CliGetApiView
from .views.logs import ApiV1CliLogsApiView
from .views.manifest import ApiV1CliManifestApiView
from .views.nonbrokered.chat import ApiV1CliChatApiView
from .views.nonbrokered.chat_config import ApiV1CliChatConfigApiView
from .views.nonbrokered.status import ApiV1CliStatusApiView
from .views.nonbrokered.version import ApiV1CliVersionApiView
from .views.nonbrokered.whoami import ApiV1CliWhoamiApiView


class ApiV1CliReverseViews:
    """Reverse views for the CLI commands"""

    manifest = "api_v1_cli_manifest_view"
    apply = "api_v1_cli_apply_view"
    chat = "api_v1_cli_chat_view"
    chat_config = "api_v1_cli_chatconfig_view"
    delete = "api_v1_cli_delete_view"
    deploy = "api_v1_cli_deploy_view"
    describe = "api_v1_cli_describe_view"
    get = "api_v1_cli_get_view"
    logs = "api_v1_cli_logs_kind_view"
    example_manifest = "api_v1_cli_manifest_view"
    status = "api_v1_cli_status_view"
    version = "api_v1_cli_version_view"
    whoami = "api_v1_cli_whoami_view"


urlpatterns = [
    path("apply/", ApiV1CliApplyApiView.as_view(), name=ApiV1CliReverseViews.apply),
    path("chat/<str:name>/", ApiV1CliChatApiView.as_view(), name=ApiV1CliReverseViews.chat),
    path("chat/config/<str:name>/", ApiV1CliChatConfigApiView.as_view(), name=ApiV1CliReverseViews.chat_config),
    path("delete/<str:kind>/", ApiV1CliDeleteApiView.as_view(), name=ApiV1CliReverseViews.delete),
    path("deploy/<str:kind>/", ApiV1CliDeployApiView.as_view(), name=ApiV1CliReverseViews.deploy),
    path("describe/<str:kind>/", ApiV1CliDescribeApiView.as_view(), name=ApiV1CliReverseViews.describe),
    path("get/<str:kind>/", ApiV1CliGetApiView.as_view(), name=ApiV1CliReverseViews.get),
    path("logs/<str:kind>/", ApiV1CliLogsApiView.as_view(), name=ApiV1CliReverseViews.logs),
    path("example_manifest/<str:kind>/", ApiV1CliManifestApiView.as_view(), name=ApiV1CliReverseViews.example_manifest),
    path("status/", ApiV1CliStatusApiView.as_view(), name=ApiV1CliReverseViews.status),
    path("version/", ApiV1CliVersionApiView.as_view(), name=ApiV1CliReverseViews.version),
    path("whoami/", ApiV1CliWhoamiApiView.as_view(), name=ApiV1CliReverseViews.whoami),
]
