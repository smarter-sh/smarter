"""
URL configuration for Smarter deployed Chatbots.

Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Endpoint
     - Description
   * - /
     - Named chatbot configuration view
   * - /config/
     - Named chatbot configuration view
   * - /chat/
     - Default chatbot API view

.. seealso::

    - :class:`smarter.apps.prompt.views.ChatConfigView`
    - :class:`smarter.apps.chatbot.api.v1.views.default.DefaultChatbotApiView`
"""

# from django.contrib import admin
from django.urls import path

from smarter.apps.chatbot.api.v1.views.default import DefaultChatbotApiView
from smarter.apps.prompt.views import ChatConfigView

urlpatterns = [
    path("", ChatConfigView.as_view(), name="root_home"),
    path("config/", ChatConfigView.as_view(), name="chatbot_named_config"),
    path("chat/", DefaultChatbotApiView.as_view(), name="chatbot_named_chat"),
]

__all__ = ["urlpatterns"]
