"""
URL configuration for Smarter deployed LLMClients.

Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Endpoint
     - Description
   * - /
     - Named llmclient configuration view
   * - /config/
     - Named llmclient configuration view
   * - /prompt/
     - Default llmclient API view

.. seealso::

    - :class:`smarter.apps.prompt.views.PromptConfigView`
    - :class:`smarter.apps.llmclient.api.v1.views.default.DefaultLLMClientApiView`
"""

# from django.contrib import admin
from django.urls import path

from smarter.apps.llmclient.api.v1.views.default import DefaultLLMClientApiView
from smarter.apps.prompt.views.detailviews import PromptConfigView

urlpatterns = [
    path("", PromptConfigView.as_view(), name="console_home"),
    path("config/", PromptConfigView.as_view(), name="llmclient_named_config"),
    path("prompt/", DefaultLLMClientApiView.as_view(), name="llmclient_named_chat"),
]

__all__ = ["urlpatterns"]
