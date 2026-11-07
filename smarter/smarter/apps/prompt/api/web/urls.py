"""
URL configuration for the Prompt app's endpoints in the web console's api.

These are mounted at ``/api/web/prompt/``. The LLMClient list page's React app calls the list,
clone, rename and delete endpoints (see :mod:`smarter.apps.prompt.views.listview.api`), and the Prompt
Engineer's Workbench calls an LLMClient's endpoints, under ``llm-clients/<hashed_id>/``: its manifest,
for the Manifest tab's editor, its architecture, its deployment, and the deployment's api key
actions (see :mod:`smarter.apps.prompt.views.detailviews`). See :mod:`smarter.apps.api.web`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.prompt.const import namespace
from smarter.apps.prompt.views.detailviews import (
    LLMClientArchitectureView,
    LLMClientDeploymentApiKeyAttachView,
    LLMClientDeploymentApiKeyCreateView,
    LLMClientDeploymentApiKeyDetachView,
    LLMClientDeploymentView,
    LLMClientManifestEditorView,
)
from smarter.apps.prompt.views.listview.api import (
    PromptListApiCloneView,
    PromptListApiDeleteView,
    PromptListApiRenameView,
    PromptListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class PromptApiWebReverseNames:
    """
    Reverse view names for the Prompt app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(PromptApiWebReverseNames.namespace, PromptApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(PromptListApiView.__name__)
    listview_all = to_snake_case(PromptListApiView.__name__) + "_all"
    clone = to_snake_case(PromptListApiCloneView.__name__)
    delete = to_snake_case(PromptListApiDeleteView.__name__)
    rename = to_snake_case(PromptListApiRenameView.__name__)

    manifest_editor_by_hashed_id = to_snake_case(LLMClientManifestEditorView.__name__)
    architecture_by_hashed_id = to_snake_case(LLMClientArchitectureView.__name__)
    deployment_by_hashed_id = to_snake_case(LLMClientDeploymentView.__name__)
    deployment_api_key_create_by_hashed_id = to_snake_case(LLMClientDeploymentApiKeyCreateView.__name__)
    deployment_api_key_attach_by_hashed_id = to_snake_case(LLMClientDeploymentApiKeyAttachView.__name__)
    deployment_api_key_detach_by_hashed_id = to_snake_case(LLMClientDeploymentApiKeyDetachView.__name__)


urlpatterns = [
    path("listview/", PromptListApiView.as_view(), name=PromptApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        PromptListApiView.as_view(),
        name=PromptApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:llmclient_id>/<str:new_name>/",
        PromptListApiCloneView.as_view(),
        name=PromptApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:llmclient_id>/",
        PromptListApiDeleteView.as_view(),
        name=PromptApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:llmclient_id>/<str:new_name>/",
        PromptListApiRenameView.as_view(),
        name=PromptApiWebReverseNames.rename,
    ),
    # --------------------------------------------------------------------------
    # an LLMClient's endpoints, which the Prompt Engineer's Workbench calls
    # --------------------------------------------------------------------------
    path(
        "llm-clients/<str:hashed_id>/manifest/",
        LLMClientManifestEditorView.as_view(),
        name=PromptApiWebReverseNames.manifest_editor_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/architecture/",
        LLMClientArchitectureView.as_view(),
        name=PromptApiWebReverseNames.architecture_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/deployment/",
        LLMClientDeploymentView.as_view(),
        name=PromptApiWebReverseNames.deployment_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/deployment/api-keys/create/",
        LLMClientDeploymentApiKeyCreateView.as_view(),
        name=PromptApiWebReverseNames.deployment_api_key_create_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/deployment/api-keys/attach/",
        LLMClientDeploymentApiKeyAttachView.as_view(),
        name=PromptApiWebReverseNames.deployment_api_key_attach_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/deployment/api-keys/detach/",
        LLMClientDeploymentApiKeyDetachView.as_view(),
        name=PromptApiWebReverseNames.deployment_api_key_detach_by_hashed_id,
    ),
]
