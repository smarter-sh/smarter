"""
URL configuration for Smarter API v1.

This module defines the ``urlpatterns`` for the ``/api/v1/`` entry point and
delegates route handling to app-specific URL modules.

**Routes**

- ``accounts/``: User account management endpoints.
- ``llm_clients/``: LLMClient CRUD and related operations.
- ``cli/``: Brokered services for CLI workflows.
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
from smarter.apps.api.v1.tests import urls as tests_urls
from smarter.apps.connection.api.v1 import urls as connection_urls
from smarter.apps.llm_client.api.v1 import urls as llm_client_urls
from smarter.apps.llm_client.const import namespace as llm_client_namespace
from smarter.apps.plugin.api.v1 import urls as plugin_urls
from smarter.apps.plugin.const import namespace as plugin_namespace
from smarter.apps.prompt.api.v1 import urls as prompt_urls
from smarter.apps.prompt.const import namespace as prompt_namespace
from smarter.apps.provider.api.v1 import urls as provider_urls
from smarter.apps.provider.const import namespace as provider_namespace
from smarter.apps.secret.api.v1 import urls as secret_urls
from smarter.apps.secret.const import namespace as secret_namespace
from smarter.apps.vectorstore.api.v1 import urls as vectorstore_urls
from smarter.common.conf import smarter_settings
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

from .cli.const import namespace as cli_namespace
from .const import namespace

logger = logging.getLogger(__name__)

app_name = namespace

# /api/v1/ is the main entry point for the API
urlpatterns = [
    # for LLMClients of the form https://example.3141-5926-5359.alpha.api.example.com
    # path("", include(llm_client_urls)),
    # -------------------------------------------
    # the main API
    # -------------------------------------------
    path("accounts/", include(account_urls, namespace=account_namespace)),
    path("llm-clients/", include(llm_client_urls, namespace=llm_client_namespace)),
    path("cli/", include(cli_urls, namespace=cli_namespace)),
    path("connections/", include(connection_urls, namespace="connection")),
    path("plugins/", include(plugin_urls, namespace=plugin_namespace)),
    path("prompts/", include(prompt_urls, namespace=prompt_namespace)),
    path("providers/", include(provider_urls, namespace=provider_namespace)),
    path("secrets/", include(secret_urls, namespace=secret_namespace)),
    path("tests/", include(tests_urls, namespace="tests")),
]

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
