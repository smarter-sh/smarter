"""
Django URL patterns for the prompt app.

These are the
endpoints for for the Workbench React app and prompt configuration.

how we got here:
 - /
 - /workbench/<str:name>/config/
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.detailviews import (
    LLMClientArchitectureView,
    LLMClientDeploymentApiKeyAttachView,
    LLMClientDeploymentApiKeyCreateView,
    LLMClientDeploymentApiKeyDetachView,
    LLMClientDeploymentView,
    LLMClientDetailView,
    LLMClientManifestEditorView,
    PromptConfigView,
    PromptSandboxView,
    PromptWorkbenchView,
)
from .views.listview import (
    PromptListView,
)

app_name = namespace


class PromptReverseNames:
    """
    Reverse views for the Prompt app.

    Provides named references for reversing Prompt-related API endpoints.

    This class is used for reverse URL resolution in Django, where each attribute
    corresponds to a Prompt command endpoint. The names are derived from the actual
    API view class names, ensuring consistency and reducing the risk of typos
    when using Django's URL reversing features.

    All Prompt endpoints in the Smarter platform are included as attributes
    of this class. This centralizes the reverse URL names for all Prompt endpoints,
    making it easier to maintain and reference them throughout the codebase. The
    endpoints that the LLMClient list page's React app calls are in the web console's
    api: see :class:`smarter.apps.prompt.api.web.urls.PromptApiWebReverseNames`.

    Usage
    -----
    Use these attributes with Django's ``reverse()`` function or in templates
    to generate URLs for Prompt API endpoints based on the view class names.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse
        url = reverse(PromptReverseNames.describe, kwargs={'hashed_id': 'rMTAwMDAzOQx'})

        # returns manifest of the llmclient with the given hashed_id
        retval = PromptReverseNames.describe
        print(retval)
    """

    namespace = namespace

    manifest_by_hashed_id = to_snake_case(LLMClientDetailView.__name__)
    manifest_editor_by_hashed_id = to_snake_case(LLMClientManifestEditorView.__name__)
    architecture_by_hashed_id = to_snake_case(LLMClientArchitectureView.__name__)
    deployment_by_hashed_id = to_snake_case(LLMClientDeploymentView.__name__)
    deployment_api_key_create_by_hashed_id = to_snake_case(LLMClientDeploymentApiKeyCreateView.__name__)
    deployment_api_key_attach_by_hashed_id = to_snake_case(LLMClientDeploymentApiKeyAttachView.__name__)
    deployment_api_key_detach_by_hashed_id = to_snake_case(LLMClientDeploymentApiKeyDetachView.__name__)
    chat_by_hashed_id = to_snake_case(PromptWorkbenchView.__name__)
    config_by_hashed_id = to_snake_case(PromptConfigView.__name__)
    sandbox_by_hashed_id = to_snake_case(PromptSandboxView.__name__)

    listview = to_snake_case(PromptListView.__name__)


urlpatterns = [
    path("", PromptListView.as_view(), name=PromptReverseNames.listview),
    path("llm-clients/<str:hashed_id>/", PromptSandboxView.as_view(), name=PromptReverseNames.sandbox_by_hashed_id),
    path(
        "llm-clients/<str:hashed_id>/manifest/",
        LLMClientDetailView.as_view(),
        name=PromptReverseNames.manifest_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/manifest/editor/",
        LLMClientManifestEditorView.as_view(),
        name=PromptReverseNames.manifest_editor_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/architecture/",
        LLMClientArchitectureView.as_view(),
        name=PromptReverseNames.architecture_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/deployment/",
        LLMClientDeploymentView.as_view(),
        name=PromptReverseNames.deployment_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/deployment/api-keys/create/",
        LLMClientDeploymentApiKeyCreateView.as_view(),
        name=PromptReverseNames.deployment_api_key_create_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/deployment/api-keys/attach/",
        LLMClientDeploymentApiKeyAttachView.as_view(),
        name=PromptReverseNames.deployment_api_key_attach_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/deployment/api-keys/detach/",
        LLMClientDeploymentApiKeyDetachView.as_view(),
        name=PromptReverseNames.deployment_api_key_detach_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/prompt/",
        PromptWorkbenchView.as_view(),
        name=PromptReverseNames.chat_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/config/", PromptConfigView.as_view(), name=PromptReverseNames.config_by_hashed_id
    ),
]
