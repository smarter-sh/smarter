"""
Smarter API command-line interface URL configuration.

- https://api.smarter.sh/v1/cli/apply/          # Apply a manifest
- https://api.smarter.sh/v1/cli/describe/       # print the manifest
- https://api.smarter.sh/v1/cli/deploy/         # Deploy a resource
- https://api.smarter.sh/v1/cli/logs/           # Get logs for a resource
- https://api.smarter.sh/v1/cli/delete/         # Delete a resource
- https://api.smarter.sh/v1/cli/status/         # Smarter platform status
"""

from django.urls import path

from .views.apply import ApiV1CliApplyApiView
from .views.delete import ApiV1CliDeleteApiView
from .views.deploy import ApiV1CliDeployApiView
from .views.describe import ApiV1CliDescribeApiView
from .views.logs import ApiV1CliLogsApiView
from .views.manifest import ApiV1CliManifestApiView
from .views.status import ApiV1CliStatusApiView
from .views.whoami import ApiV1CliWhoamiApiView


urlpatterns = [
    path("apply/", ApiV1CliApplyApiView.as_view(), name="api_v1_cli_apply_view"),
    path("describe/<str:kind>/<str:name>/", ApiV1CliDescribeApiView.as_view(), name="api_v1_cli_describe_view"),
    path("deploy/<str:kind>/<str:name>/", ApiV1CliDeployApiView.as_view(), name="api_v1_cli_deploy_view"),
    path("logs/<str:kind>/<str:name>/", ApiV1CliLogsApiView.as_view(), name="api_v1_cli_logs_kind_name_view"),
    path("logs/<str:kind>/", ApiV1CliLogsApiView.as_view(), name="api_v1_cli_logs_kind_view"),
    path("logs/", ApiV1CliLogsApiView.as_view(), name="api_v1_cli_logs_view"),
    path("delete/<str:kind>/<str:name>/", ApiV1CliDeleteApiView.as_view(), name="api_v1_cli_delete_view"),
    path("status/", ApiV1CliStatusApiView.as_view(), name="api_v1_cli_status_view"),
    path("manifest/<str:kind>/", ApiV1CliManifestApiView.as_view(), name="api_v1_cli_manifest_view"),
    path("whoami/", ApiV1CliWhoamiApiView.as_view(), name="api_v1_cli_whoami_view"),
]
