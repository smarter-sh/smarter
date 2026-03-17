"""
Django URL patterns for the prompt app. These are the
endpoints for for the Workbench React app and chat configuration.

how we got here:
 - /
 - /workbench/<str:name>/config/
"""

from django.urls import include, path

from .api.const import namespace as api_namespace
from .const import namespace
from .views import (
    ChatAppWorkbenchView,
    ChatConfigView,
    PromptListView,
    PromptManifestView,
)

app_name = namespace

urlpatterns = [
    path("", PromptListView.as_view(), name="listview"),
    path("api/", include("smarter.apps.prompt.api.urls", namespace=api_namespace)),
    path("chatbots/<str:hashed_id>/manifest/", PromptManifestView.as_view(), name="prompt_manifest_by_hashed_id"),
    path("chatbots/<str:hashed_id>/chat/", ChatAppWorkbenchView.as_view(), name="prompt_chat_by_hashed_id"),
    path("chatbots/<str:hashed_id>/config/", ChatConfigView.as_view(), name="prompt_config_by_hashed_id"),
]
