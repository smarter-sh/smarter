"""
Smarter API command-line interface URL configuration.

- https://api.smarter.sh/v0/cli/apply/          # Apply a manifest
- https://api.smarter.sh/v0/cli/describe/       # print the manifest
- https://api.smarter.sh/v0/cli/deploy/         # Deploy a resource
- https://api.smarter.sh/v0/cli/logs/           # Get logs for a resource
- https://api.smarter.sh/v0/cli/delete/         # Delete a resource
- https://api.smarter.sh/v0/cli/status/         # Smarter platform status
"""

from django.urls import path

from .views.apply import CliApplyManifestApiView
from .views.delete import CliDeleteObjectApiView
from .views.deploy import CliDeployApiView
from .views.describe import CliDescribeApiView
from .views.logs import CliLogsApiView
from .views.manifest import CliManifestExampleApiView
from .views.status import CliPlatformStatusApiView
from .views.whoami import CliPlatformWhoamiApiView


urlpatterns = [
    path("apply/", CliApplyManifestApiView.as_view(), name="cli_apply_view"),
    path("describe/<str:kind>/<str:name>/", CliDescribeApiView.as_view(), name="cli_describe_view"),
    path("deploy/<str:kind>/<str:name>/", CliDeployApiView.as_view(), name="cli_deploy_view"),
    path("logs/<str:kind>/<str:name>/", CliLogsApiView.as_view(), name="cli_logs_view"),
    path("logs/<str:kind>/", CliLogsApiView.as_view(), name="cli_logs_view"),
    path("logs/", CliLogsApiView.as_view(), name="cli_logs_view"),
    path("delete/<str:kind>/<str:name>/", CliDeleteObjectApiView.as_view(), name="cli_delete_view"),
    path("status/", CliPlatformStatusApiView.as_view(), name="cli_status_view"),
    path("manifest/<str:kind>/", CliManifestExampleApiView.as_view(), name="cli_manifest_view"),
    path("whoami/", CliPlatformWhoamiApiView.as_view(), name="cli_whoami_view"),
]
