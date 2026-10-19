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

The api views answer POST. While the ``enable_llmclient_endpoints_page`` waffle switch is active, a GET
or HEAD of any of them, e.g. from a browser, receives a page with the curl commands that call them.

.. seealso::

    - :class:`smarter.apps.prompt.views.PromptConfigView`
    - :class:`smarter.apps.llmclient.api.v1.views.default.DefaultLLMClientApiView`
    - :class:`smarter.apps.llmclient.views.endpoints.LLMClientEndpointsView`
"""

# from django.contrib import admin
from django.urls import path

from smarter.apps.llmclient.api.v1.views.default import DefaultLLMClientApiView
from smarter.apps.llmclient.views.endpoints import browser_friendly
from smarter.apps.prompt.views.detailviews import PromptConfigView

config_view = browser_friendly(PromptConfigView.as_view())

urlpatterns = [
    path("", config_view, name="llmclient_config"),
    # Alias for 'console_home' so that templates shared with the web console
    # (e.g. error pages) can resolve this name regardless of which
    # django-hosts urlconf is active for the current request.
    path("", config_view, name="console_home"),
    path("config/", config_view, name="llmclient_named_config"),
    path("prompt/", browser_friendly(DefaultLLMClientApiView.as_view()), name="llmclient_named_chat"),
]

__all__ = ["urlpatterns"]
