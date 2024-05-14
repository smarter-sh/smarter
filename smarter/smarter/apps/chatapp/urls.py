"""Django URL patterns for the chatapp"""

from django.urls import path

from .views import ChatAppView, ChatConfigView


urlpatterns = [
    path("", ChatAppView.as_view(), name="chatapp"),
    path("<str:name>/", ChatAppView.as_view(), name="chatapp_chatbot_name"),
    path("<str:name>/config/", ChatConfigView.as_view(), name="chatapp_chatbot_config"),
]
