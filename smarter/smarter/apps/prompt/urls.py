"""
Django URL patterns for the chatapp

how we got here:
 - /
 - /workbench/<str:name>/config/
 - also via smarter.urls.py config_redirector() ???

"""

from django.urls import path

from .const import namespace
from .views import ChatAppWorkbenchView, ChatConfigView, PromptListView


app_name = namespace

urlpatterns = [
    path("", PromptListView.as_view(), name="listview"),
    path("<str:name>/chat/", ChatAppWorkbenchView.as_view(), name="by_name"),
    path("<str:name>/config/", ChatConfigView.as_view(), name="by_name_config"),
]
