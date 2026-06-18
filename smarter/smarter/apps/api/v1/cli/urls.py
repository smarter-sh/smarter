"""
URL configuration for the Smarter API command-line interface (CLI).

Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Endpoint
     - Description
   * - /api/v1/cli/get/
     - Return information about the specified resource
   * - /api/v1/cli/apply/
     - Apply a manifest
   * - /api/v1/cli/describe/
     - Print the manifest
   * - /api/v1/cli/deploy/
     - Deploy a resource
   * - /api/v1/cli/logs/
     - Get logs for a resource
   * - /api/v1/cli/delete/
     - Delete a resource
   * - /api/v1/cli/status/
     - Smarter platform status
   * - /api/v1/cli/version/
     - Returns detailed version information on the platform
   * - /api/v1/cli/whoami/
     - Return information about the current IAM user
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.apply import ApiV1CliApplyApiView
from .views.delete import ApiV1CliDeleteApiView
from .views.deploy import ApiV1CliDeployApiView
from .views.describe import ApiV1CliDescribeApiView
from .views.get import ApiV1CliGetApiView
from .views.logs import ApiV1CliLogsApiView
from .views.manifest import ApiV1CliManifestApiView
from .views.nonbrokered.prompt import ApiV1CliPromptApiView
from .views.nonbrokered.prompt_config import ApiV1CliPromptConfigApiView
from .views.nonbrokered.status import ApiV1CliStatusApiView
from .views.nonbrokered.version import ApiV1CliVersionApiView
from .views.nonbrokered.whoami import ApiV1CliWhoamiApiView
from .views.schema import ApiV1CliSchemaApiView
from .views.undeploy import ApiV1CliUndeployApiView

app_name = namespace


class ApiV1CliReverseViews:
    """
    Reverse views for the CLI commands.

    Provides named references for reversing CLI-related API endpoints.

    This class is used for reverse URL resolution in Django, where each attribute
    corresponds to a CLI command endpoint. The names are derived from the actual
    API view class names, ensuring consistency and reducing the risk of typos
    when using Django's URL reversing features.

    All CLI commands available in the Smarter platform are included as attributes
    of this class. This centralizes the reverse URL names for all CLI endpoints,
    making it easier to maintain and reference them throughout the codebase.

    Usage
    -----
    Use these attributes with Django's ``reverse()`` function or in templates
    to generate URLs for CLI API endpoints based on the view class names.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse
        url = reverse(ApiV1CliReverseViews.deploy, kwargs={'kind': 'Plugin'})

        str(ApiV1CliReverseViews.deploy)
        returns 'api_v1_cli_deploy_api_view'
    """

    namespace = f"api:v1:{namespace}:"

    manifest = to_snake_case(ApiV1CliManifestApiView)
    apply = to_snake_case(ApiV1CliApplyApiView)
    prompt = to_snake_case(ApiV1CliPromptApiView)
    chat_config = to_snake_case(ApiV1CliPromptConfigApiView)
    delete = to_snake_case(ApiV1CliDeleteApiView)
    deploy = to_snake_case(ApiV1CliDeployApiView)
    undeploy = to_snake_case(ApiV1CliUndeployApiView)
    describe = to_snake_case(ApiV1CliDescribeApiView)
    get = to_snake_case(ApiV1CliGetApiView)
    logs = to_snake_case(ApiV1CliLogsApiView)
    example_manifest = to_snake_case(ApiV1CliManifestApiView)
    status = to_snake_case(ApiV1CliStatusApiView)
    json_schema = to_snake_case(ApiV1CliSchemaApiView)
    version = to_snake_case(ApiV1CliVersionApiView)
    whoami = to_snake_case(ApiV1CliWhoamiApiView)


urlpatterns = [
    path("apply/", ApiV1CliApplyApiView.as_view(), name=ApiV1CliReverseViews.apply),
    path("prompt/<str:name>/", ApiV1CliPromptApiView.as_view(), name=ApiV1CliReverseViews.prompt),
    path("prompt/config/<str:name>/", ApiV1CliPromptConfigApiView.as_view(), name=ApiV1CliReverseViews.chat_config),
    path("delete/<str:kind>/", ApiV1CliDeleteApiView.as_view(), name=ApiV1CliReverseViews.delete),
    path("deploy/<str:kind>/", ApiV1CliDeployApiView.as_view(), name=ApiV1CliReverseViews.deploy),
    path("undeploy/<str:kind>/", ApiV1CliUndeployApiView.as_view(), name=ApiV1CliReverseViews.undeploy),
    path("describe/<str:kind>/", ApiV1CliDescribeApiView.as_view(), name=ApiV1CliReverseViews.describe),
    path("get/<str:kind>/", ApiV1CliGetApiView.as_view(), name=ApiV1CliReverseViews.get),
    path("logs/<str:kind>/", ApiV1CliLogsApiView.as_view(), name=ApiV1CliReverseViews.logs),
    path("example-manifest/<str:kind>/", ApiV1CliManifestApiView.as_view(), name=ApiV1CliReverseViews.example_manifest),
    path("json-schema/<str:kind>/", ApiV1CliSchemaApiView.as_view(), name=ApiV1CliReverseViews.json_schema),
    path("status/", ApiV1CliStatusApiView.as_view(), name=ApiV1CliReverseViews.status),
    path("version/", ApiV1CliVersionApiView.as_view(), name=ApiV1CliReverseViews.version),
    path("whoami/", ApiV1CliWhoamiApiView.as_view(), name=ApiV1CliReverseViews.whoami),
]
