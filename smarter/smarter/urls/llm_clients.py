"""
URL configuration for Smarter deployed LLMClients.

Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Endpoint
     - Description
   * - /
     - Named llm_client configuration view
   * - /config/
     - Named llm_client configuration view
   * - /chat/
     - Default llm_client API view

.. seealso::

    - :class:`smarter.apps.prompt.views.ChatConfigView`
    - :class:`smarter.apps.llm_client.api.v1.views.default.DefaultLLMClientApiView`
"""

# from django.contrib import admin
from django.urls import path

from smarter.apps.llm_client.api.v1.views.default import DefaultLLMClientApiView
from smarter.apps.prompt.views.detailview import ChatConfigView

urlpatterns = [
    path("", ChatConfigView.as_view(), name="console_home"),
    path("config/", ChatConfigView.as_view(), name="llm_client_named_config"),
    path("chat/", DefaultLLMClientApiView.as_view(), name="llm_client_named_chat"),
]

__all__ = ["urlpatterns"]
