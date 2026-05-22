"""
Django URL patterns for the prompt app. These are the
endpoints for for the Workbench React app and chat configuration.

how we got here:
 - /
 - /workbench/<str:name>/config/
"""

from django.urls import path, re_path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.detailview import (
    ChatAppWorkbenchView,
    ChatConfigView,
    PromptLandingView,
    PromptManifestView,
)
from .views.listview import (
    PromptListView,
)
from .views.listview.api import (
    PromptListApiCloneView,
    PromptListApiDeleteView,
    PromptListApiRenameView,
    PromptListApiView,
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
    making it easier to maintain and reference them throughout the codebase.

    Usage
    -----
    Use these attributes with Django's ``reverse()`` function or in templates
    to generate URLs for Prompt API endpoints based on the view class names.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse
        url = reverse(PromptReverseNames.describe, kwargs={'hashed_id': 'rMTAwMDAzOQx'})

        # returns manifest of the chatbot with the given hashed_id
        retval = PromptReverseNames.describe
        print(retval)

    """

    namespace = namespace

    manifest_by_hashed_id = to_snake_case(PromptManifestView)
    chat_by_hashed_id = to_snake_case(ChatAppWorkbenchView)
    config_by_hashed_id = to_snake_case(ChatConfigView)
    landing_by_hashed_id = to_snake_case(PromptLandingView)

    listview = to_snake_case(PromptListView)
    listview_api = to_snake_case(PromptListApiView)
    listview_api_all = to_snake_case(PromptListApiView) + "_all"
    listview_api_clone = to_snake_case(PromptListApiCloneView)
    listview_api_delete = to_snake_case(PromptListApiDeleteView)
    listview_api_rename = to_snake_case(PromptListApiRenameView)


urlpatterns = [
    path("", PromptListView.as_view(), name=PromptReverseNames.listview),
    path("api/listview/", PromptListApiView.as_view(), name=PromptReverseNames.listview_api_all),
    re_path(
        r"^api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        PromptListApiView.as_view(),
        name=PromptReverseNames.listview_api,
    ),
    path(
        "api/listview/clone/<int:chatbot_id>/<str:new_name>/",
        PromptListApiCloneView.as_view(),
        name=PromptReverseNames.listview_api_clone,
    ),
    path(
        "api/listview/delete/<int:chatbot_id>/",
        PromptListApiDeleteView.as_view(),
        name=PromptReverseNames.listview_api_delete,
    ),
    path(
        "api/listview/rename/<int:chatbot_id>/<str:new_name>/",
        PromptListApiRenameView.as_view(),
        name=PromptReverseNames.listview_api_rename,
    ),
    path("chatbots/<str:hashed_id>/", PromptLandingView.as_view(), name=PromptReverseNames.landing_by_hashed_id),
    path(
        "chatbots/<str:hashed_id>/manifest/",
        PromptManifestView.as_view(),
        name=PromptReverseNames.manifest_by_hashed_id,
    ),
    path(
        "chatbots/<str:hashed_id>/chat/",
        ChatAppWorkbenchView.as_view(),
        name=PromptReverseNames.chat_by_hashed_id,
    ),
    path("chatbots/<str:hashed_id>/config/", ChatConfigView.as_view(), name=PromptReverseNames.config_by_hashed_id),
]
