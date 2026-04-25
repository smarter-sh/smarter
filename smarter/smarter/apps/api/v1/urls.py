"""
URL configuration for the Smarter API V1. The `urlpatterns`
list in this module maps URL patterns to their corresponding views or sub-URL configurations. This enables Django to route incoming HTTP requests to the appropriate logic for handling API operations.

**Structure**

- The root path (`""`) includes the chatbot API, supporting endpoints such as `https://example.3141-5926-5359.alpha.api.example.com`.
- The following subpaths are defined for the main API:

  - ``accounts/``: User account management (CRUD operations).
  - ``chatbots/``: Management of chatbot resources (CRUD operations).
  - ``prompts/``: Endpoints supporting client-side interactions with chatbots.
  - ``plugins/``: Management of plugins and connections to external services.
  - ``providers/``: Management of provider integrations.
  - ``cli/``: Brokered services supporting the CLI, implemented within this module.
  - ``tests/``: Endpoints for unit testing, implemented within this module.

Namespaces are used for each included URL configuration to avoid naming conflicts and to provide clear separation between different API components.

.. seealso::

    `Django URL dispatcher documentation <https://docs.djangoproject.com/en/5.0/topics/http/urls/>`_

"""

import logging

from django.urls import include, path

from smarter.apps.account.api.v1 import urls as account_urls
from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.api.v1.cli import urls as cli_urls
from smarter.apps.api.v1.tests import urls as tests_urls
from smarter.apps.chatbot.api.v1 import urls as chatbot_urls
from smarter.apps.chatbot.const import namespace as chatbot_namespace
from smarter.apps.connection.api.v1 import urls as connection_urls
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
from smarter.common.helpers.console_helpers import formatted_text

from .cli.const import namespace as cli_namespace
from .const import namespace

logger = logging.getLogger(__name__)

app_name = namespace

# /api/v1/ is the main entry point for the API
urlpatterns = [
    # for Chatbots of the form https://example.3141-5926-5359.alpha.api.example.com
    path("", include(chatbot_urls)),
    # -------------------------------------------
    # the main API
    # -------------------------------------------
    path("accounts/", include(account_urls, namespace=account_namespace)),
    path("chatbots/", include(chatbot_urls, namespace=chatbot_namespace)),
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
    logger.info("%s Vectorstore API endpoints enabled.", formatted_text(__name__))
else:
    logger.info(
        "%s Vectorstore API endpoints have been disabled. Set env `SMARTER_ENABLE_VECTORSTORE=true` to enable.",
        formatted_text(__name__),
    )
