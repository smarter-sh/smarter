"""
Django URL patterns for the prompt app. These are the
endpoints for for the Workbench React app and chat configuration.

how we got here:
 - /
 - /workbench/<str:name>/config/
 - also via smarter.urls.py config_redirector() ???

"""

from django.urls import include, path

from .api.const import namespace as api_namespace
from .const import namespace
from .views import ChatAppWorkbenchView, ChatConfigView, PromptListView


app_name = namespace

urlpatterns = [
    path("", PromptListView.as_view(), name="listview"),
    path("api/", include("smarter.apps.prompt.api.urls", namespace=api_namespace)),
    path("<str:name>/chat/", ChatAppWorkbenchView.as_view(), name="by_name"),
    path("<str:name>/config/", ChatConfigView.as_view(), name="by_name_config"),
]
