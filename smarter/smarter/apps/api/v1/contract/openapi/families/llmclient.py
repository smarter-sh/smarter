"""The LLMClients' REST reads, under ``/api/v1/llm-clients/``.

Their chat api is in :mod:`smarter.apps.api.v1.contract.openapi.chat`.
"""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import OpenApiPathItem
from smarter.apps.api.v1.contract.openapi.builders import (
    ApiFamily,
    id_or_hashed_id,
    integer_id,
    rest_read,
)
from smarter.apps.llmclient.const import namespace
from smarter.apps.llmclient.contract.models import (
    LLMClientApiCustomDomain,
    LLMClientApiExtension,
    LLMClientApiKey,
    LLMClientApiLLMClient,
    LLMClientApiPlugin,
)

LLMCLIENTS = ApiFamily(
    name=namespace,
    resource=SAMKinds.LLM_CLIENT.value,
    urlconf="smarter.apps.llmclient.api.v1.urls",
    description="The {plural}' REST reads.",
    mount="llm-clients",
)
"""The LLMClients' family: its REST reads, and the chat api, whose routes it shares."""

LLMCLIENT_ID_PARAMETER = id_or_hashed_id(LLMCLIENTS.resource)
"""The ``{id}`` of an LLMClient's routes: its numeric id or its hashed id."""


def llmclient_paths() -> dict[str, OpenApiPathItem]:
    """
    The REST reads of the LLMClients, relative to the server's ``/api/v1``.

    An LLMClient is read by its numeric id or its hashed id. Its related rows, by its numeric id only:
    their routes take no hashed id.

    :returns: The paths, e.g. ``{"/llm-clients/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = LLMCLIENTS
    resource = family.resource
    llmclient_id = integer_id("id", f"The {resource}'s numeric id.")

    def read(action, summary, description, item, parameters, many=False):
        return rest_read(
            family.operation_id(action), summary, description, family.tag, item, many=many, parameters=parameters
        )

    reads = {
        family.path(): read(
            "list",
            f"List {family.plural}",
            f"The {family.plural} that the user may read.",
            LLMClientApiLLMClient.__name__,
            [],
            many=True,
        ),
        family.path("{id}/"): read(
            "retrieve",
            family.a_capitalized,
            f"{family.a_capitalized}, with its extensions, plugins, custom domains, api keys and urls.",
            LLMClientApiLLMClient.__name__,
            [LLMCLIENT_ID_PARAMETER],
        ),
        family.path("{id}/plugins/"): read(
            "plugin_list",
            f"{family.a_capitalized}'s plugins",
            f"The plugins of {family.a}, each with the plugin's metadata.",
            LLMClientApiPlugin.__name__,
            [llmclient_id],
            many=True,
        ),
        family.path("{id}/plugins/{plugin_id}/"): read(
            "plugin_retrieve",
            f"A plugin of {family.a}",
            f"A plugin of {family.a}, by the {resource}Plugin's id.",
            LLMClientApiPlugin.__name__,
            [llmclient_id, integer_id("plugin_id", f"The {resource}Plugin's id.")],
        ),
        family.path("{id}/apikeys/"): read(
            "apikey_list",
            f"{family.a_capitalized}'s api keys",
            f"The api keys of {family.a}: the ids of their SmarterAuthTokens, never the keys.",
            LLMClientApiKey.__name__,
            [llmclient_id],
            many=True,
        ),
        family.path("{id}/apikeys/{apikey_id}/"): read(
            "apikey_retrieve",
            f"An api key of {family.a}",
            f"An api key of {family.a}, by the LLMClientAPIKey's id.",
            LLMClientApiKey.__name__,
            [llmclient_id, integer_id("apikey_id", "The LLMClientAPIKey's id.")],
        ),
        family.path("{id}/customdomains"): read(
            "customdomain_list",
            f"{family.a_capitalized}'s custom domains",
            f"The custom domain of {family.a}, as a list of none or one.",
            LLMClientApiCustomDomain.__name__,
            [llmclient_id],
            many=True,
        ),
        family.path("{id}/customdomains/{customdomain_id}"): read(
            "customdomain_retrieve",
            f"A custom domain of {family.a}",
            f"A custom domain of {family.a}, by its id.",
            LLMClientApiCustomDomain.__name__,
            [llmclient_id, integer_id("customdomain_id", f"The {resource}CustomDomain's id.")],
        ),
        family.path("{id}/extensions"): read(
            "extension_list",
            f"{family.a_capitalized}'s extensions",
            f"The extensions whose tools {family.a} offers the LLM.",
            LLMClientApiExtension.__name__,
            [llmclient_id],
            many=True,
        ),
        family.path("{id}/extensions/{extension_id}"): read(
            "extension_retrieve",
            f"An extension of {family.a}",
            f"An extension of {family.a}, by the {resource}Extensions' id.",
            LLMClientApiExtension.__name__,
            [llmclient_id, integer_id("extension_id", f"The {resource}Extensions' id.")],
        ),
    }
    return {path: OpenApiPathItem(get=operation) for path, operation in reads.items()}


__all__ = ["LLMCLIENTS", "LLMCLIENT_ID_PARAMETER", "llmclient_paths"]
