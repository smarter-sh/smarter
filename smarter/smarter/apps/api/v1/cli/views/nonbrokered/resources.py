# pylint: disable=W0613
"""
Smarter API command-line interface 'resources' view.

Generates a list of dicts describing every resource
in SAMKinds.

Example:

retval = {
    "data": [
        {
            "Singular": "Plugin",
            "Plural": "Plugins",
            "APIKind": "Plugin",
            "Display": "Plugin",
            "DisplayPlural": "Plugins",
            "Deployable": False,
        },
        {
            "Singular": "ApiPlugin",
            "Plural": "ApiPlugins",
            "APIKind": "ApiPlugin",
            "Display": "ApiPlugin",
            "DisplayPlural": "ApiPlugins",
            "Deployable": False,
        },
        {
            "Singular": "SkillPlugin",
            "Plural": "SkillPlugins",
            "APIKind": "SkillPlugin",
            "Display": "SkillPlugin",
            "DisplayPlural": "SkillPlugins",
            "Deployable": False,
        },
        {
            "Singular": "SqlPlugin",
            "Plural": "SqlPlugins",
            "APIKind": "SqlPlugin",
            "Display": "SqlPlugin",
            "DisplayPlural": "SqlPlugins",
            "Deployable": False,
        },
        {
            "Singular": "ApiConnection",
            "Plural": "ApiConnections",
            "APIKind": "ApiConnection",
            "Display": "ApiConnection",
            "DisplayPlural": "ApiConnections",
            "Deployable": False,
        },
        {
            "Singular": "SqlConnection",
            "Plural": "SqlConnections",
            "APIKind": "SqlConnection",
            "Display": "SqlConnection",
            "DisplayPlural": "SqlConnections",
            "Deployable": False,
        },
        {
            "Singular": "Account",
            "Plural": "Accounts",
            "APIKind": "Account",
            "Display": "Account",
            "DisplayPlural": "Accounts",
            "Deployable": False,
        },
        {
            "Singular": "SmarterAuthToken",
            "Plural": "SmarterAuthTokens",
            "APIKind": "SmarterAuthToken",
            "Display": "SmarterAuthToken",
            "DisplayPlural": "SmarterAuthTokens",
            "Deployable": False,
        },
        {
            "Singular": "User",
            "Plural": "Users",
            "APIKind": "User",
            "Display": "User",
            "DisplayPlural": "Users",
            "Deployable": False,
        },
        {
            "Singular": "Secret",
            "Plural": "Secrets",
            "APIKind": "Secret",
            "Display": "Secret",
            "DisplayPlural": "Secrets",
            "Deployable": False,
        },
        {
            "Singular": "Guardrail",
            "Plural": "Guardrails",
            "APIKind": "Guardrail",
            "Display": "Guardrail",
            "DisplayPlural": "Guardrails",
            "Deployable": False,
        },
        {
            "Singular": "Prompt",
            "Plural": "Prompts",
            "APIKind": "Prompt",
            "Display": "Prompt",
            "DisplayPlural": "Prompts",
            "Deployable": True,
        },
        {
            "Singular": "LLMClient",
            "Plural": "LLMClients",
            "APIKind": "LLMClient",
            "Display": "LLMClient",
            "DisplayPlural": "LLMClients",
            "Deployable": False,
        },
        {
            "Singular": "LLMHost",
            "Plural": "LLMHosts",
            "APIKind": "LLMHost",
            "Display": "LLMHost",
            "DisplayPlural": "LLMHosts",
            "Deployable": False,
        },
        {
            "Singular": "MCPClient",
            "Plural": "MCPClients",
            "APIKind": "MCPClient",
            "Display": "MCPClient",
            "DisplayPlural": "MCPClients",
            "Deployable": False,
        },
        {
            "Singular": "Orchestrator",
            "Plural": "Orchestrators",
            "APIKind": "Orchestrator",
            "Display": "Orchestrator",
            "DisplayPlural": "Orchestrators",
            "Deployable": False,
        },
        {
            "Singular": "Provider",
            "Plural": "Providers",
            "APIKind": "Provider",
            "Display": "Provider",
            "DisplayPlural": "Providers",
            "Deployable": False,
        },
        {
            "Singular": "Proxy",
            "Plural": "Proxies",
            "APIKind": "Proxy",
            "Display": "Proxy",
            "DisplayPlural": "Proxies",
            "Deployable": False,
        },
        {
            "Singular": "Vectorsearch",
            "Plural": "Vectorsearches",
            "APIKind": "Vectorsearch",
            "Display": "Vectorsearch",
            "DisplayPlural": "Vectorsearches",
            "Deployable": False,
        },
        {
            "Singular": "Vectorstore",
            "Plural": "Vectorstores",
            "APIKind": "Vectorstore",
            "Display": "Vectorstore",
            "DisplayPlural": "Vectorstores",
            "Deployable": False,
        },
    ],
    "api": "smarter.sh/v1",
    "metadata": {"command": "version", "thing": "None"},
}
"""

from http import HTTPStatus

from django.http import JsonResponse

from smarter.apps.api.v1.cli.views.base import CliBaseApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.journal.http import SmarterJournaledJsonResponse


class ApiV1CliResourcesApiView(CliBaseApiView):
    """Smarter API command-line interface 'resources' view."""

    def dictionaryize(self, sam_kind: str, deployable: bool = False) -> dict:

        sam_kind_singular = SAMKinds.str_to_kind(sam_kind)
        sam_kind_plural = SAMKinds.plural(sam_kind_singular)
        return {
            "Singular": sam_kind_singular,
            "Plural": sam_kind_plural,
            "APIKind": sam_kind_singular,
            "Display": sam_kind_singular,
            "DisplayPlural": sam_kind_plural,
            "Deployable": deployable,
        }

    def resources(self):

        all_resources = []
        all_kinds = SAMKinds.all()
        for kind in all_kinds:
            deployable = kind == SAMKinds.PROMPT.value
            kind_dict = self.dictionaryize(sam_kind=kind, deployable=deployable)
            all_resources.append(kind_dict)

        try:
            data = {SmarterJournalApiResponseKeys.DATA: all_resources}

            return SmarterJournaledJsonResponse(
                request=self.request,
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.VERSION),
                data=data,
                status=HTTPStatus.OK.value,
            )
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(data={"error": str(e)}, status=HTTPStatus.BAD_REQUEST.value)

    def post(self, request):
        response = self.resources()
        return response
