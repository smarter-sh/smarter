"""
Django URL patterns for the prompt app: the Prompt Engineer's Workbench, at ``/workbench/``.

The workbench's pages, an LLMClient's manifest page, and the LLMClient's chat configuration, which
Smarter Chat also reads from the public api, ``/api/v1/llm-clients/<hashed_id>/config/``. The
endpoints that the workbench's React app calls are in the web console's api, at
``/api/web/prompt/``: see :mod:`smarter.apps.prompt.api.web.urls`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.detailviews import (
    LLMClientDetailView,
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
    endpoints that the LLMClient list page's and the workbench's React apps call are in the
    web console's api: see :class:`smarter.apps.prompt.api.web.urls.PromptApiWebReverseNames`.

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
        "llm-clients/<str:hashed_id>/prompt/",
        PromptWorkbenchView.as_view(),
        name=PromptReverseNames.chat_by_hashed_id,
    ),
    path(
        "llm-clients/<str:hashed_id>/config/", PromptConfigView.as_view(), name=PromptReverseNames.config_by_hashed_id
    ),
]
