"""
URL configuration for Smarter API v1.

This module defines the ``urlpatterns`` for the ``/api/v1/`` entry point and
delegates route handling to app-specific URL modules.

**Routes**

- ``accounts/``: User account management endpoints.
- ``llmclients/``: LLMClient CRUD and related operations.
- ``cli/``: Brokered services for CLI workflows.
- ``demos/``: Fictional data for the platform's example resources, e.g. the Stackademy course catalogue.
- ``mcp/``: The Smarter Project MCP server, which reads the project's documentation and code.
- ``journal/``: Smarter Journal entries (superusers only).
- ``connections/``: External connection integration endpoints.
- ``plugins/``: Plugin management endpoints.
- ``prompts/``: Prompt and interaction endpoints.
- ``providers/``: Provider integration endpoints.
- ``secrets/``: Secret management endpoints.
- ``tests/``: Test-only endpoints.
- ``vectorstores/``: Vector store endpoints (enabled only when
    ``SMARTER_ENABLE_VECTORSTORE=true``).

Each included URL set uses a namespace to avoid naming collisions and to keep
API components logically separated.

.. seealso::

        `Django URL dispatcher documentation <https://docs.djangoproject.com/en/5.0/topics/http/urls/>`_
"""

from django.urls import include, path

from smarter.apps.account.api.v1 import urls as account_urls
from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.api.v1.cli import urls as cli_urls
from smarter.apps.api.v1.demos import urls as demos_urls
from smarter.apps.api.v1.tests import urls as tests_urls
from smarter.apps.connection.api.v1 import urls as connection_urls
from smarter.apps.connection.const import namespace as connnection_namespace
from smarter.apps.guardrail.api.v1 import urls as guardrail_urls
from smarter.apps.guardrail.const import namespace as guardrail_namespace
from smarter.apps.llmclient.api.v1 import urls as llmclient_urls
from smarter.apps.llmclient.const import namespace as llmclient_namespace
from smarter.apps.llmhost.api.v1 import urls as llmhost_urls
from smarter.apps.llmhost.const import namespace as llmhost_namespace
from smarter.apps.llmtool.api.v1 import urls as llmtool_urls
from smarter.apps.llmtool.const import namespace as llmtool_namespace
from smarter.apps.mcpclient.api.v1 import urls as mcpclient_urls
from smarter.apps.mcpclient.const import namespace as mcpclient_namespace
from smarter.apps.mcpserver import urls as mcpserver_urls
from smarter.apps.mcpserver.const import namespace as mcpserver_namespace
from smarter.apps.orchestrator.api.v1 import urls as orchestrator_urls
from smarter.apps.orchestrator.const import namespace as orchestrator_namespace
from smarter.apps.prompt.api.v1 import urls as prompt_urls
from smarter.apps.prompt.const import namespace as prompt_namespace
from smarter.apps.provider.api.v1 import urls as provider_urls
from smarter.apps.provider.const import namespace as provider_namespace
from smarter.apps.proxy.api.v1 import urls as proxy_urls
from smarter.apps.proxy.const import namespace as proxy_namespace
from smarter.apps.secret.api.v1 import urls as secret_urls
from smarter.apps.secret.const import namespace as secret_namespace
from smarter.apps.vectorsearch.api.v1 import urls as vectorsearch_urls
from smarter.apps.vectorsearch.const import namespace as vectorsearch_namespace
from smarter.apps.vectorstore.api.v1 import urls as vectorstore_urls
from smarter.common.conf import smarter_settings
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging
from smarter.lib.journal.api.v1 import urls as journal_urls
from smarter.lib.journal.const import namespace as journal_namespace

from .cli.const import namespace as cli_namespace
from .const import namespace
from .demos.const import namespace as demos_namespace

logger = logging.getLogger(__name__)

app_name = namespace

# /api/v1/ is the main entry point for the API
urlpatterns = [
    # for LLMClients of the form https://example.3141-5926-5359.alpha.api.example.com
    # path("", include(llmclient_urls)),
    # -------------------------------------------
    # the main API
    # -------------------------------------------
    path("accounts/", include(account_urls, namespace=account_namespace)),
    path("llm-clients/", include(llmclient_urls, namespace=llmclient_namespace)),
    path("llmhosts/", include(llmhost_urls, namespace=llmhost_namespace)),
    path("mcpclients/", include(mcpclient_urls, namespace=mcpclient_namespace)),
    path("mcp/", include(mcpserver_urls, namespace=mcpserver_namespace)),
    path("cli/", include(cli_urls, namespace=cli_namespace)),
    path("demos/", include(demos_urls, namespace=demos_namespace)),
    path("connections/", include(connection_urls, namespace=connnection_namespace)),
    path("guardrails/", include(guardrail_urls, namespace=guardrail_namespace)),
    path("journal/", include(journal_urls, namespace=journal_namespace)),
    path("orchestrators/", include(orchestrator_urls, namespace=orchestrator_namespace)),
    path("plugins/", include(llmtool_urls, namespace=llmtool_namespace)),
    path("prompts/", include(prompt_urls, namespace=prompt_namespace)),
    path("providers/", include(provider_urls, namespace=provider_namespace)),
    path("secrets/", include(secret_urls, namespace=secret_namespace)),
    path("tests/", include(tests_urls, namespace="tests")),
    path("vectorsearches/", include(vectorsearch_urls, namespace=vectorsearch_namespace)),
]

if smarter_settings.enable_proxy:
    urlpatterns += [
        path("proxy/", include(proxy_urls, namespace=proxy_namespace)),
    ]
    logger.info("%s Proxy API endpoints are %s.", logging.formatted_text(__name__), SmarterReadyState.READY)
else:
    logger.info(
        "%s Proxy API endpoints are %s. Set env `SMARTER_ENABLE_PROXY=true` to enable.",
        logging.formatted_text(__name__),
        SmarterReadyState.NOT_READY,
    )
if smarter_settings.enable_vectorstore:
    urlpatterns += [
        path("vectorstores/", include(vectorstore_urls, namespace="vectorstore")),
    ]
    logger.info("%s Vectorstore API endpoints are %s.", logging.formatted_text(__name__), SmarterReadyState.READY)
else:
    logger.info(
        "%s Vectorstore API endpoints are %s. Set env `SMARTER_ENABLE_VECTORSTORE=true` to enable.",
        logging.formatted_text(__name__),
        SmarterReadyState.NOT_READY,
    )
