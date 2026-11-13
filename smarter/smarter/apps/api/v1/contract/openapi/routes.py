"""
Which routes of ``/api/v1`` the document covers, and why it leaves out the others.

``test_every_route_is_documented`` and ``test_every_family_is_covered`` hold the document to these tables: every
route of a family in :data:`DOCUMENTED_URLCONFS` must be in the document, or in :data:`UNDOCUMENTED_ROUTES`,
and every family that ``smarter.apps.api.v1.urls`` mounts must be in :data:`DOCUMENTED_URLCONFS`, or in
:data:`UNDOCUMENTED_URLCONFS`.
"""

from smarter.apps.connection.const import namespace as connection_namespace

from .builders import plural
from .cli import CLI_PREFIX, CLI_URLCONF
from .families import (
    ACCOUNTS,
    FAMILIES,
    GUARDRAILS,
    HISTORY,
    LLMCLIENTS,
    LLMHOSTS,
    MCPCLIENTS,
    ORCHESTRATORS,
    PLUGINS,
    PROXIES,
    SECRETS,
    VECTORSEARCHES,
    VECTORSTORES,
)

CONNECTIONS_PREFIX = f"/{plural(connection_namespace)}/"
"""The path of the connections' routes, a family that has none to document: its urlconf has no routes."""

DOCUMENTED_URLCONFS: dict[str, str] = {
    CLI_PREFIX: CLI_URLCONF,
    CONNECTIONS_PREFIX: "smarter.apps.connection.api.v1.urls",
    **{family.prefix: family.urlconf for family in FAMILIES},
}
"""
The families of routes that the document covers: each one's path, relative to ``/api/v1``, and its urlconf.

The cli api's, the connections', and each of :data:`~smarter.apps.api.v1.contract.openapi.families.FAMILIES`.
Every route of these urlconfs must be in the document, or in :data:`UNDOCUMENTED_ROUTES`.
"""

UNDOCUMENTED_URLCONFS: dict[str, str] = {
    "/tests/": "Views that only the platform's own unit tests call.",
    "/doodles/": (
        "The sign-in page's doodle of the day and its artwork, smarter.apps.doodle, which only the "
        "page's own React app reads. These are not part of the platform's api."
    ),
    "/demos/": (
        "Fictional data for the platform's example resources, e.g. the Stackademy course catalogue "
        "that the Stackademy ApiPlugin queries. These are not part of the platform's api."
    ),
    "/mcp/": (
        "The MCPServer, smarter.apps.mcpserver: a JSON-RPC endpoint for its public tools and one for its "
        "staff-only tools, whose methods and messages the Model Context Protocol specification defines, not OpenAPI."
    ),
}
"""
The families of routes under ``/api/v1`` that the document leaves out, and why.

Every family that ``smarter.apps.api.v1.urls`` mounts must be in :data:`DOCUMENTED_URLCONFS` or here.
"""

ID_FAMILIES = (LLMCLIENTS, GUARDRAILS, SECRETS, MCPCLIENTS, VECTORSTORES, LLMHOSTS, ORCHESTRATORS, VECTORSEARCHES)
"""The families whose routes take ``<int:<name>_id>``, e.g. ``<int:guardrail_id>``, beside ``<str:hashed_id>``."""

PATH_PARAMETER_ALIASES: dict[str, str] = {
    "hashed_id": "id",
    "pk": "id",
    **{f"{family.name}_id": "id" for family in ID_FAMILIES},
}
"""
The document's names of the routes' path parameters, where they differ.

A resource's routes take either its numeric id or its hashed id, e.g. ``<int:guardrail_id>`` and
``<str:hashed_id>``, which the document describes as one ``{id}``.
"""

NOT_YET_MODELED = "Not modeled yet. The REST reads of each resource family are the next part of the contract."

WEB_CONSOLE = "A web console action, which clients replace with the cli api's manifests."

PROVIDER_PASSTHROUGH = "A Proxy's passthrough, whose requests and responses are its provider's api, not Smarter's."

UNDOCUMENTED_ROUTES: dict[str, str] = {
    PLUGINS.path("{plugin_id}/clone/{new_name}"): WEB_CONSOLE,
    PLUGINS.path("upload/"): WEB_CONSOLE,
    PROXIES.path("{name}/"): PROVIDER_PASSTHROUGH,
    PROXIES.path("{name}/{path}"): PROVIDER_PASSTHROUGH,
    LLMCLIENTS.path("{id}/prompt/config/"): f"A legacy alias of {LLMCLIENTS.path('{id}/config/')}, for pages that "
    "installed an older Smarter Chat.",
    ACCOUNTS.path("batch-create-users/"): "Creates users from a CSV file in the web console. Clients apply User "
    "manifests with the cli api.",
    HISTORY.path("smarter/{provider_name}/"): "The chat api of an LLM provider through Smarter, whose requests and "
    "responses are the provider's, not Smarter's.",
    HISTORY.path("passthrough/{provider_name}/"): "A passthrough to an LLM provider's api, whose requests and "
    "responses are the provider's, not Smarter's.",
    ORCHESTRATORS.path(f"{{id}}/{ORCHESTRATORS.name}/"): f"Running {ORCHESTRATORS.a} is not implemented yet: the "
    "route has no POST handler, and answers 405.",
}
"""The paths of the routes of :data:`DOCUMENTED_URLCONFS` that the document leaves out, and why."""

__all__ = [
    "CONNECTIONS_PREFIX",
    "DOCUMENTED_URLCONFS",
    "ID_FAMILIES",
    "NOT_YET_MODELED",
    "PATH_PARAMETER_ALIASES",
    "PROVIDER_PASSTHROUGH",
    "UNDOCUMENTED_ROUTES",
    "UNDOCUMENTED_URLCONFS",
    "WEB_CONSOLE",
]
