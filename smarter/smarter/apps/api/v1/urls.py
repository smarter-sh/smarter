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

from django.urls import include, path

from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.chatbot.const import namespace as chatbot_namespace
from smarter.apps.plugin.const import namespace as plugin_namespace
from smarter.apps.prompt.const import namespace as prompt_namespace
from smarter.apps.provider.const import namespace as provider_namespace

from .cli.const import namespace as cli_namespace
from .const import namespace


app_name = namespace

# /api/v1/ is the main entry point for the API
urlpatterns = [
    # for Chatbots of the form https://example.3141-5926-5359.alpha.api.example.com
    path("", include("smarter.apps.chatbot.api.v1.urls")),
    # -------------------------------------------
    # for the main API:
    # /api/v1/account/ is used for user account management CRUD operations
    # /api/v1/chatbots/ is used for managing chatbot CRUD operations
    # /api/v1/prompt/ is used for supporting client-side interactions with the chatbots.
    # /api/v1/plugins/ is used for managing plugins and connections to external services.
    # /api/v1/cli/ implements Brokered services that support the CLI, and is implemented here, in this module.
    # /api/v1/tests/ is used for unit tests, and is implemented here, in this module.
    # -------------------------------------------
    path("accounts/", include("smarter.apps.account.api.v1.urls", namespace=account_namespace)),
    path("chatbots/", include("smarter.apps.chatbot.api.v1.urls", namespace=chatbot_namespace)),
    path("prompts/", include("smarter.apps.prompt.api.v1.urls", namespace=prompt_namespace)),
    path("plugins/", include("smarter.apps.plugin.api.v1.urls", namespace=plugin_namespace)),
    path("providers/", include("smarter.apps.provider.api.v1.urls", namespace=provider_namespace)),
    path("cli/", include("smarter.apps.api.v1.cli.urls", namespace=cli_namespace)),
    path("tests/", include("smarter.apps.api.v1.tests.urls", namespace="tests")),
]
