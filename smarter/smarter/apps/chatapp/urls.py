"""Django URL patterns for the chatapp"""

from django.urls import path

from .views import ChatAppView


urlpatterns = [
    path("", ChatAppView.as_view(), name="chatapp"),
    path("chatbots/<str:name>/", ChatAppView.as_view(), name="chatapp_chatbot_name"),
]
