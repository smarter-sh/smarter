# pylint: disable=W0613
"""
API view for the Dashboard "Quick Actions" React component.

Returns links to the web console pages that users visit most, so that the
React component does not hard-code console URLs. Superusers also get links to
the pages that only they may open: Extensions and Infrastructure Resources.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.models import get_resolved_user
from smarter.apps.account.views.budget.urls import BudgetReverseNames
from smarter.apps.guardrail.urls import GuardrailReverseNames
from smarter.apps.llmtool.urls import PluginReverseNames
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.apps.secret.urls import SecretReverseNames
from smarter.lib.cache import cache_results
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedWebView

DOCS_URL = "https://docs.smarter.sh/"


@cache_results()
def get_quick_actions(is_superuser: bool = False) -> list[dict[str, str]]:
    """
    The quick action links, which are the same for every user of the same role.

    :param is_superuser: Whether to add the links to the pages that only superusers may open.
    :type is_superuser: bool
    :returns: The quick actions, in the order the dashboard shows them.
    :rtype: list[dict[str, str]]
    """
    # imported here, because the dashboard's urls import this module.
    # pylint: disable=import-outside-toplevel
    from smarter.apps.dashboard.context_processors import sidebar_context

    sidebar = sidebar_context()["sidebar"]
    retval = [
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
            "name": "Guardrails",
            "description": "Screen prompts and responses",
            "icon": "ki-shield-tick",
            "url": reverse(GuardrailReverseNames.namespace, GuardrailReverseNames.listview),
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
    ]
    if sidebar.get("manifest_drop_zone"):
        retval.append(
            {
                "name": "Apply Manifest",
                "description": "Drop in a YAML manifest",
                "icon": "ki-file-up",
                "url": sidebar["manifest_drop_zone"],
            }
        )
    if is_superuser:
        retval += [
            {
                "name": "Extensions",
                "description": "Install from the registry",
                "icon": "ki-element-plus",
                "url": sidebar["extensions"],
            },
            {
                "name": "Infrastructure",
                "description": "DNS, certificates, Kubernetes",
                "icon": "ki-cloud",
                "url": sidebar["infrastructure_resources"],
            },
        ]
    retval += [
        {
            "name": "API Reference",
            "description": "This platform's OpenAPI document",
            "icon": "ki-code",
            "url": sidebar["openapi"],
        },
        {
            "name": "Documentation",
            "description": "docs.smarter.sh",
            "icon": "ki-book-open",
            "url": DOCS_URL,
        },
    ]
    return retval


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
        user = get_resolved_user(request.user)
        is_superuser = bool(user and user.is_superuser)
        return JsonResponse(get_quick_actions(is_superuser=is_superuser), status=HTTPStatus.OK, safe=False)
