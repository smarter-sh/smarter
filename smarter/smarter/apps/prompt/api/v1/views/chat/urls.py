"""URL configuration for chat app."""

from django.urls import path

from .const import namespace
from .passthrough import PassthroughChatViewSet
from .smarter import SmarterChatApiViewSet

app_name = namespace

urlpatterns = [
    path("smarter/<str:provider_name>/", SmarterChatApiViewSet.as_view(), name="smarter-chat-api"),
    path("passthrough/<str:provider_name>/", PassthroughChatViewSet.as_view(), name="passthrough-chat-api"),
]
