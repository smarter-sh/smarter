"""
Smarter API command-line interface URL configuration.

- https://platform.smarter.sh/api/v1/cli/get/            # Return information about the  specified resource
- https://platform.smarter.sh/api/v1/cli/apply/          # Apply a manifest
- https://platform.smarter.sh/api/v1/cli/describe/       # print the manifest
- https://platform.smarter.sh/api/v1/cli/deploy/         # Deploy a resource
- https://platform.smarter.sh/api/v1/cli/logs/           # Get logs for a resource
- https://platform.smarter.sh/api/v1/cli/delete/         # Delete a resource
- https://platform.smarter.sh/api/v1/cli/status/         # Smarter platform status
"""

from django.urls import path

from .views.apply import ApiV1CliApplyApiView
from .views.delete import ApiV1CliDeleteApiView
from .views.deploy import ApiV1CliDeployApiView
from .views.describe import ApiV1CliDescribeApiView
from .views.get import ApiV1CliGetApiView
from .views.logs import ApiV1CliLogsApiView
from .views.manifest import ApiV1CliManifestApiView
from .views.status import ApiV1CliStatusApiView
from .views.whoami import ApiV1CliWhoamiApiView


urlpatterns = [
    path("apply/", ApiV1CliApplyApiView.as_view(), name="api_v1_cli_apply_view"),
    path("delete/<str:kind>/<str:name>/", ApiV1CliDeleteApiView.as_view(), name="api_v1_cli_delete_view"),
    path("deploy/<str:kind>/<str:name>/", ApiV1CliDeployApiView.as_view(), name="api_v1_cli_deploy_view"),
    path("describe/<str:kind>/<str:name>/", ApiV1CliDescribeApiView.as_view(), name="api_v1_cli_describe_view"),
    path("get/<str:kind>/", ApiV1CliGetApiView.as_view(), name="api_v1_cli_get_view"),
    path("get/<str:kind>/<name:str>", ApiV1CliGetApiView.as_view(), name="api_v1_cli_get_view"),
    path("logs/<str:kind>/<str:name>/", ApiV1CliLogsApiView.as_view(), name="api_v1_cli_logs_kind_name_view"),
    path("logs/<str:kind>/", ApiV1CliLogsApiView.as_view(), name="api_v1_cli_logs_kind_view"),
    path("logs/", ApiV1CliLogsApiView.as_view(), name="api_v1_cli_logs_view"),
    path("manifest/<str:kind>/", ApiV1CliManifestApiView.as_view(), name="api_v1_cli_manifest_view"),
    path("status/", ApiV1CliStatusApiView.as_view(), name="api_v1_cli_status_view"),
    path("whoami/", ApiV1CliWhoamiApiView.as_view(), name="api_v1_cli_whoami_view"),
]
