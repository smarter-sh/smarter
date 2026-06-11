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
   * - /prompt/
     - Default llm_client API view

.. seealso::

    - :class:`smarter.apps.prompt.views.PromptConfigView`
    - :class:`smarter.apps.llm_client.api.v1.views.default.DefaultLLMClientApiView`
"""

# from django.contrib import admin
from django.urls import path

from smarter.apps.llm_client.api.v1.views.default import DefaultLLMClientApiView
from smarter.apps.prompt.views.detailviews import PromptConfigView

urlpatterns = [
    path("", PromptConfigView.as_view(), name="console_home"),
    path("config/", PromptConfigView.as_view(), name="llm_client_named_config"),
    path("prompt/", DefaultLLMClientApiView.as_view(), name="llm_client_named_chat"),
]

__all__ = ["urlpatterns"]
