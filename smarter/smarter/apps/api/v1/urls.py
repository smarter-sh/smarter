"""
URL configuration for smarter api.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
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
    # for Chatbots of the form https://example.3141-5926-5359.alpha.api.smarter.sh
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
