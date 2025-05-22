"""Django URL patterns for the chatapp"""

from django.urls import path

from .views import ChatAppListView, ChatAppWorkbenchView, ChatConfigView


# how we got here: /chatbots/<str:name>/config/
# also via smarter.urls.py config_redirector() ???
urlpatterns = [
    path("", ChatAppListView.as_view(), name="chatbots"),
    path("<str:name>/", ChatAppWorkbenchView.as_view(), name="chatapp_chatbot_name"),
    path("<str:name>/config/", ChatConfigView.as_view(), name="chatapp_chatbot_config"),
]
