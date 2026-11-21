"""
URL configuration for the web console's api, mounted at ``/api/web/``.

Each Django app that has a console page with a React app mounts its endpoints here, under its
app label, from its own ``api/web/urls.py``, e.g. ``/api/web/guardrail/listview/``. The
endpoints are internal to the web console: see :mod:`smarter.apps.api.web`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import include, path

from smarter.apps.account.api.web import urls as account_web_urls
from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.api.web.session.views import ConsoleSessionView
from smarter.apps.connection.api.web import urls as connection_web_urls
from smarter.apps.connection.const import namespace as connection_namespace
from smarter.apps.dashboard.api.web import urls as dashboard_web_urls
from smarter.apps.dashboard.const import namespace as dashboard_namespace
from smarter.apps.guardrail.api.web import urls as guardrail_web_urls
from smarter.apps.guardrail.const import namespace as guardrail_namespace
from smarter.apps.infrastructure.api.web import urls as infrastructure_web_urls
from smarter.apps.infrastructure.const import namespace as infrastructure_namespace
from smarter.apps.llmclient.api.web import urls as llmclient_web_urls
from smarter.apps.llmclient.const import namespace as llmclient_namespace
from smarter.apps.llmhost.api.web import urls as llmhost_web_urls
from smarter.apps.llmhost.const import namespace as llmhost_namespace
from smarter.apps.llmtool.api.web import urls as llmtool_web_urls
from smarter.apps.llmtool.const import namespace as llmtool_namespace
from smarter.apps.mcpclient.api.web import urls as mcpclient_web_urls
from smarter.apps.mcpclient.const import namespace as mcpclient_namespace
from smarter.apps.orchestrator.api.web import urls as orchestrator_web_urls
from smarter.apps.orchestrator.const import namespace as orchestrator_namespace
from smarter.apps.prompt.api.web import urls as prompt_web_urls
from smarter.apps.prompt.const import namespace as prompt_namespace
from smarter.apps.provider.api.web import urls as provider_web_urls
from smarter.apps.provider.const import namespace as provider_namespace
from smarter.apps.proxy.api.web import urls as proxy_web_urls
from smarter.apps.proxy.const import namespace as proxy_namespace
from smarter.apps.secret.api.web import urls as secret_web_urls
from smarter.apps.secret.const import namespace as secret_namespace
from smarter.apps.vectorsearch.api.web import urls as vectorsearch_web_urls
from smarter.apps.vectorsearch.const import namespace as vectorsearch_namespace
from smarter.apps.vectorstore.api.web import urls as vectorstore_web_urls
from smarter.apps.vectorstore.const import namespace as vectorstore_namespace
from smarter.common.conf import smarter_settings
from smarter.common.utils import to_snake_case
from smarter.lib.drf.api.web import urls as drf_web_urls
from smarter.lib.drf.const import namespace as drf_namespace
from smarter.lib.manifest.sam_apps import SamAppUrls, sam_app_urlpatterns

from .const import namespace, path_namespace

app_name = namespace


class ApiWebReverseNames:
    """The names of the web console api's own urls, the ones that belong to no Django app."""

    namespace = path_namespace

    console_session_view = to_snake_case(ConsoleSessionView.__name__)


urlpatterns = [
    path("session/", ConsoleSessionView.as_view(), name=ApiWebReverseNames.console_session_view),
    path(f"{account_namespace}/", include(account_web_urls, namespace=account_namespace)),
    # the one path that isn't its namespace: it matches the console page, /authtoken/.
    path("authtoken/", include(drf_web_urls, namespace=drf_namespace)),
    path(f"{dashboard_namespace}/", include(dashboard_web_urls, namespace=dashboard_namespace)),
    path(f"{infrastructure_namespace}/", include(infrastructure_web_urls, namespace=infrastructure_namespace)),
    path(f"{prompt_namespace}/", include(prompt_web_urls, namespace=prompt_namespace)),
]

SAM_APP_WEB_API_URLS: list[SamAppUrls] = [
    SamAppUrls(
        "enable_connection", "Connection", f"{connection_namespace}/", connection_web_urls, connection_namespace
    ),
    SamAppUrls("enable_guardrail", "Guardrail", f"{guardrail_namespace}/", guardrail_web_urls, guardrail_namespace),
    SamAppUrls("enable_llmclient", "LLMClient", f"{llmclient_namespace}/", llmclient_web_urls, llmclient_namespace),
    SamAppUrls("enable_llmhost", "LLMHost", f"{llmhost_namespace}/", llmhost_web_urls, llmhost_namespace),
    SamAppUrls("enable_llmtool", "LLMTool", f"{llmtool_namespace}/", llmtool_web_urls, llmtool_namespace),
    SamAppUrls("enable_mcpclient", "MCPClient", f"{mcpclient_namespace}/", mcpclient_web_urls, mcpclient_namespace),
    SamAppUrls(
        "enable_orchestrator",
        "Orchestrator",
        f"{orchestrator_namespace}/",
        orchestrator_web_urls,
        orchestrator_namespace,
    ),
    SamAppUrls("enable_provider", "Provider", f"{provider_namespace}/", provider_web_urls, provider_namespace),
    SamAppUrls("enable_proxy", "Proxy", f"{proxy_namespace}/", proxy_web_urls, proxy_namespace),
    SamAppUrls("enable_secret", "Secret", f"{secret_namespace}/", secret_web_urls, secret_namespace),
    SamAppUrls(
        "enable_vectorsearch",
        "VectorSearch",
        f"{vectorsearch_namespace}/",
        vectorsearch_web_urls,
        vectorsearch_namespace,
    ),
    SamAppUrls(
        "enable_vectorstore",
        "Vectorstore",
        f"{vectorstore_namespace}/",
        vectorstore_web_urls,
        vectorstore_namespace,
    ),
]
"""
The web console api endpoints of the SAM resource apps.

Each app's endpoints are mounted only if its ``smarter_settings.enable_<app>`` flag is true. See
:mod:`smarter.lib.manifest.sam_apps`.
"""

urlpatterns += sam_app_urlpatterns(smarter_settings, SAM_APP_WEB_API_URLS, "web console api endpoints")
