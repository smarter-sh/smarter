# pylint: disable=W0613
"""
Smarter API command-line interface 'resources' view.

{
        {Singular: "apiconnection", Plural: "apiconnections", APIKind: "ApiConnection", Display: "ApiConnection", DisplayPlural: "ApiConnections"},
        {Singular: "sqlconnection", Plural: "sqlconnections", APIKind: "SqlConnection", Display: "SqlConnection", DisplayPlural: "SqlConnections"},
        {Singular: "apikey", Plural: "apikeys", APIKind: "SmarterAuthToken", Display: "SmarterAuthToken", DisplayPlural: "SmarterAuthTokens"},
        {Singular: "apiplugin", Plural: "apiplugins", APIKind: "ApiPlugin", Display: "ApiPlugin", DisplayPlural: "ApiPlugins"},
        {Singular: "sqlplugin", Plural: "sqlplugins", APIKind: "SqlPlugin", Display: "SqlPlugin", DisplayPlural: "SqlPlugins"},
        {Singular: "skillplugin", Plural: "skillplugins", APIKind: "SkillPlugin", Display: "SkillPlugin", DisplayPlural: "SkillPlugins"},
        {Singular: "guardrail", Plural: "guardrails", APIKind: "Guardrail", Display: "Guardrail", DisplayPlural: "Guardrails"},
        {Singular: "llmclient", Plural: "llmclients", APIKind: "LlmClient", Display: "LlmClient", DisplayPlural: "LlmClients"},
        {Singular: "llmhost", Plural: "llmhosts", APIKind: "LLMHost", Display: "LLMHost", DisplayPlural: "LLMHosts"},
        {Singular: "mcpclient", Plural: "mcpclients", APIKind: "MCPClient", Display: "MCPClient", DisplayPlural: "MCPClients"},
        {Singular: "orchestrator", Plural: "orchestrators", APIKind: "Orchestrator", Display: "Orchestrator", DisplayPlural: "Orchestrators"},
        {Singular: "prompt", Plural: "prompts", APIKind: "Prompt", Display: "Prompt", DisplayPlural: "Prompts", Deployable: true},
        {Singular: "promptconfig", Plural: "promptconfigs", APIKind: "PromptConfig", Display: "PromptConfig", DisplayPlural: "PromptConfigs"},
        {Singular: "provider", Plural: "providers", APIKind: "Provider", Display: "Provider", DisplayPlural: "Providers"},
        {Singular: "proxy", Plural: "proxies", APIKind: "Proxy", Display: "Proxy", DisplayPlural: "Proxies"},
        {Singular: "secret", Plural: "secrets", APIKind: "Secret", Display: "Secret", DisplayPlural: "Secrets"},
        {Singular: "vectorsearch", Plural: "vectorsearches", APIKind: "Vectorsearch", Display: "Vectorsearch", DisplayPlural: "Vectorsearches"},
        {Singular: "vectorstore", Plural: "vectorstores", APIKind: "Vectorstore", Display: "Vectorstore", DisplayPlural: "Vectorstores"},
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
