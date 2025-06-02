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

from .const import namespace
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
from .views.schema import ApiV1CliSchemaApiView
from .views.undeploy import ApiV1CliUndeployApiView


app_name = namespace


class ApiV1CliReverseViews:
    """Reverse views for the CLI commands"""

    namespace = "api:v1:cli:"

    manifest = "ApiV1CliManifestApiView".lower()
    apply = "ApiV1CliChatApiView".lower()
    chat = "ApiV1CliChatConfigApiView".lower()
    chat_config = "chatconfig_view".lower()
    delete = "ApiV1CliDeleteApiView".lower()
    deploy = "ApiV1CliDeployApiView".lower()
    undeploy = "ApiV1CliUndeployApiView".lower()
    describe = "desApiV1CliDescribeApiViewcribe_view".lower()
    get = "ApiV1CliGetApiView".lower()
    logs = "ApiV1CliLogsApiView".lower()
    example_manifest = "ApiV1CliManifestApiView".lower()
    status = "ApiV1CliStatusApiView".lower()
    schema = "ApiV1CliSchemaApiView".lower()
    version = "ApiV1CliVersionApiView".lower()
    whoami = "ApiV1CliWhoamiApiView".lower()


urlpatterns = [
    path("apply/", ApiV1CliApplyApiView.as_view(), name=ApiV1CliReverseViews.apply),
    path("chat/<str:name>/", ApiV1CliChatApiView.as_view(), name=ApiV1CliReverseViews.chat),
    path("chat/config/<str:name>/", ApiV1CliChatConfigApiView.as_view(), name=ApiV1CliReverseViews.chat_config),
    path("delete/<str:kind>/", ApiV1CliDeleteApiView.as_view(), name=ApiV1CliReverseViews.delete),
    path("deploy/<str:kind>/", ApiV1CliDeployApiView.as_view(), name=ApiV1CliReverseViews.deploy),
    path("undeploy/<str:kind>/", ApiV1CliUndeployApiView.as_view(), name=ApiV1CliReverseViews.undeploy),
    path("describe/<str:kind>/", ApiV1CliDescribeApiView.as_view(), name=ApiV1CliReverseViews.describe),
    path("get/<str:kind>/", ApiV1CliGetApiView.as_view(), name=ApiV1CliReverseViews.get),
    path("logs/<str:kind>/", ApiV1CliLogsApiView.as_view(), name=ApiV1CliReverseViews.logs),
    path("example_manifest/<str:kind>/", ApiV1CliManifestApiView.as_view(), name=ApiV1CliReverseViews.example_manifest),
    path("schema/<str:kind>/", ApiV1CliSchemaApiView.as_view(), name=ApiV1CliReverseViews.schema),
    path("status/", ApiV1CliStatusApiView.as_view(), name=ApiV1CliReverseViews.status),
    path("version/", ApiV1CliVersionApiView.as_view(), name=ApiV1CliReverseViews.version),
    path("whoami/", ApiV1CliWhoamiApiView.as_view(), name=ApiV1CliReverseViews.whoami),
]
