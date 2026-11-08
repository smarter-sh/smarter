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
    path(f"{connection_namespace}/", include(connection_web_urls, namespace=connection_namespace)),
    path(f"{dashboard_namespace}/", include(dashboard_web_urls, namespace=dashboard_namespace)),
    path(f"{guardrail_namespace}/", include(guardrail_web_urls, namespace=guardrail_namespace)),
    path(f"{infrastructure_namespace}/", include(infrastructure_web_urls, namespace=infrastructure_namespace)),
    path(f"{llmclient_namespace}/", include(llmclient_web_urls, namespace=llmclient_namespace)),
    path(f"{llmhost_namespace}/", include(llmhost_web_urls, namespace=llmhost_namespace)),
    path(f"{llmtool_namespace}/", include(llmtool_web_urls, namespace=llmtool_namespace)),
    path(f"{mcpclient_namespace}/", include(mcpclient_web_urls, namespace=mcpclient_namespace)),
    path(f"{orchestrator_namespace}/", include(orchestrator_web_urls, namespace=orchestrator_namespace)),
    path(f"{prompt_namespace}/", include(prompt_web_urls, namespace=prompt_namespace)),
    path(f"{provider_namespace}/", include(provider_web_urls, namespace=provider_namespace)),
    path(f"{secret_namespace}/", include(secret_web_urls, namespace=secret_namespace)),
    path(f"{vectorsearch_namespace}/", include(vectorsearch_web_urls, namespace=vectorsearch_namespace)),
]

# the same feature flags as the console pages' in smarter.urls.console.
if smarter_settings.enable_proxy:
    urlpatterns += [
        path(f"{proxy_namespace}/", include(proxy_web_urls, namespace=proxy_namespace)),
    ]
if smarter_settings.enable_vectorstore:
    urlpatterns += [
        path(f"{vectorstore_namespace}/", include(vectorstore_web_urls, namespace=vectorstore_namespace)),
    ]
