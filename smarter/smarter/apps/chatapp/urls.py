"""
Django URL patterns for the chatapp

how we got here:
 - /
 - /workbench/<str:name>/config/
 - also via smarter.urls.py config_redirector() ???

"""

from django.urls import path

from .const import namespace
from .views import ChatAppListView, ChatAppWorkbenchView, ChatConfigView


app_name = namespace

urlpatterns = [
    path("", ChatAppListView.as_view(), name="chat_app_listview"),
    path("<str:name>/chat/", ChatAppWorkbenchView.as_view(), name="chat_app_workbench_view_by_name"),
    path("<str:name>/config/", ChatConfigView.as_view(), name="chat_app_chat_config_view_by_name"),
]
