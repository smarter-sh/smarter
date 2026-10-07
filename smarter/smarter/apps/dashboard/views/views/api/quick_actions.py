# pylint: disable=W0613
"""
API view for the Dashboard "Quick Actions" React component.

Returns links to the web console pages that users visit most, so that the
React component does not hard-code console URLs.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.views.budget.urls import BudgetReverseNames
from smarter.apps.connection.urls import ConnectionReverseNames
from smarter.apps.plugin.urls import PluginReverseNames
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.apps.secret.urls import SecretReverseNames
from smarter.lib.cache import cache_results
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedWebView

DOCS_URL = "https://docs.smarter.sh/"


@cache_results()
def get_quick_actions() -> list[dict[str, str]]:
    """The quick action links, which are the same for every user."""
    return [
        {
            "name": "Prompt Workbench",
            "description": "Chat with and edit your LLM Clients",
            "icon": "ki-message-programming",
            "url": reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
        },
        {
            "name": "Plugins",
            "description": "Tools and data for your LLM Clients",
            "icon": "ki-cube-2",
            "url": reverse(PluginReverseNames.namespace, PluginReverseNames.listview),
        },
        {
            "name": "Connections",
            "description": "REST APIs and SQL databases",
            "icon": "ki-data",
            "url": reverse(ConnectionReverseNames.namespace, ConnectionReverseNames.listview),
        },
        {
            "name": "Secrets",
            "description": "Encrypted credentials",
            "icon": "ki-lock",
            "url": reverse(SecretReverseNames.namespace, SecretReverseNames.listview),
        },
        {
            "name": "Budgets",
            "description": "Spending limits",
            "icon": "ki-dollar",
            "url": reverse(BudgetReverseNames.namespace, BudgetReverseNames.listview),
        },
        {
            "name": "Documentation",
            "description": "docs.smarter.sh",
            "icon": "ki-book-open",
            "url": DOCS_URL,
        },
    ]


class QuickActionsView(SmarterAuthenticatedWebView):
    """
    Links to the web console pages that users visit most.

    Response shape:

    .. code-block:: json

        [
            {
                "name": "Prompt Workbench",
                "description": "Chat with and edit your LLM Clients",
                "icon": "ki-message-programming",
                "url": "/workbench/"
            }
        ]
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        return JsonResponse(get_quick_actions(), status=HTTPStatus.OK, safe=False)
