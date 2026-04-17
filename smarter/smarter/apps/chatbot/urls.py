"""Django URL patterns for the Chat"""

from django.urls import include, path

from smarter.apps.chatbot.api import urls as chatbot_api_urls

from .api.const import namespace as api_namespace
from .const import namespace

app_name = namespace

urlpatterns = [
    path("api", include(chatbot_api_urls, namespace=api_namespace)),
]
