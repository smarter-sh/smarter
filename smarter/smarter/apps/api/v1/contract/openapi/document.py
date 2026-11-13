"""
The Smarter api's OpenAPI document: its metadata, its tags, and every family's paths, assembled.

``manage.py export_api_contract`` writes it to ``openapi.json``, with :func:`write_openapi`.
"""

import json

from smarter.apps.api.v1.contract.const import (
    API_VERSION,
    DEFAULT_PLATFORM_URL,
    LOCAL_PLATFORM_URL,
    OPENAPI_PATH,
    OPENAPI_VERSION,
)
from smarter.apps.api.v1.contract.models import (
    OpenApiComponents,
    OpenApiContact,
    OpenApiDocument,
    OpenApiInfo,
    OpenApiLicense,
    OpenApiSecurityScheme,
    OpenApiServer,
    OpenApiServerVariable,
)
from smarter.common.const import (
    SMARTER_PROJECT_DOCS_URL,
    SMARTER_PROJECT_WEBSITE_URL,
)

from .builders import API_KEY_AUTH, merge_paths
from .chat import CHAT_TAG, chat_paths
from .cli import CLI_TAGS, cli_paths
from .families import (
    ACCOUNTS,
    EXTENSIONS,
    GUARDRAILS,
    HISTORY,
    JOURNAL,
    LLMCLIENTS,
    LLMHOSTS,
    MCPCLIENTS,
    ORCHESTRATORS,
    PLUGINS,
    PROVIDERS,
    PROXIES,
    SECRETS,
    VECTORSEARCHES,
    VECTORSTORES,
)
from .families.account import USAGE_TAG, account_paths, usage_paths
from .families.extension import extension_paths
from .families.guardrail import guardrail_paths
from .families.history import history_paths
from .families.journal import journal_paths
from .families.llmclient import llmclient_paths
from .families.llmhost import llmhost_paths
from .families.mcpclient import mcpclient_paths
from .families.orchestrator import orchestrator_paths
from .families.plugin import plugin_paths
from .families.provider import provider_paths
from .families.proxy import proxy_paths
from .families.secret import secret_paths
from .families.vectorsearch import vectorsearch_paths
from .families.vectorstore import vectorstore_paths
from .schemas import cli_schemas


def openapi_document() -> OpenApiDocument:
    """
    The Smarter api's OpenAPI document.

    :returns: The document.
    :rtype: OpenApiDocument
    """
    schemas, _ = cli_schemas()
    return OpenApiDocument(
        openapi=OPENAPI_VERSION,
        info=OpenApiInfo(
            title="Smarter api",
            version=API_VERSION,
            summary="Apply, get, describe, validate and delete the resources that SAM manifests declare, and chat "
            f"with {LLMCLIENTS.plural}.",
            description=(
                "The api of the smarter cli and of the Smarter SDKs. Every response is journaled: its body "
                "has the journal's api and metadata, beside the command's data or message, or an error. "
                "The chat api's requests and responses are the Smarter Chat api contract's, version 2. "
                "Generated from the platform's Pydantic models by smarter.apps.api.v1.contract.openapi; "
                f"do not edit. See {SMARTER_PROJECT_DOCS_URL}."
            ),
            contact=OpenApiContact(name="The Smarter Project", url=SMARTER_PROJECT_WEBSITE_URL),
            license=OpenApiLicense(name="AGPL-3.0", url="https://www.gnu.org/licenses/agpl-3.0.html"),
        ),
        servers=[
            OpenApiServer(
                url="{platform}/api/v1",
                description="A Smarter installation.",
                variables={
                    "platform": OpenApiServerVariable(
                        default=DEFAULT_PLATFORM_URL, description="The platform's url, with its scheme."
                    )
                },
            ),
            OpenApiServer(url=f"{LOCAL_PLATFORM_URL}/api/v1", description="A local development platform."),
        ],
        security=[{API_KEY_AUTH: []}],
        tags=[
            *CLI_TAGS,
            CHAT_TAG,
            LLMCLIENTS.openapi_tag(),
            GUARDRAILS.openapi_tag(),
            SECRETS.openapi_tag(),
            MCPCLIENTS.openapi_tag(),
            VECTORSTORES.openapi_tag(),
            LLMHOSTS.openapi_tag(),
            PLUGINS.openapi_tag(),
            PROVIDERS.openapi_tag(),
            PROXIES.openapi_tag(),
            ACCOUNTS.openapi_tag(),
            HISTORY.openapi_tag(),
            JOURNAL.openapi_tag(),
            ORCHESTRATORS.openapi_tag(),
            VECTORSEARCHES.openapi_tag(),
            USAGE_TAG,
            EXTENSIONS.openapi_tag(),
        ],
        paths=merge_paths(
            cli_paths(),
            chat_paths(),
            llmclient_paths(),
            guardrail_paths(),
            secret_paths(),
            mcpclient_paths(),
            vectorstore_paths(),
            llmhost_paths(),
            plugin_paths(),
            provider_paths(),
            proxy_paths(),
            account_paths(),
            history_paths(),
            journal_paths(),
            orchestrator_paths(),
            vectorsearch_paths(),
            usage_paths(),
            extension_paths(),
        ),
        components=OpenApiComponents(
            schemas=schemas,
            securitySchemes={
                API_KEY_AUTH: OpenApiSecurityScheme(
                    name="Authorization", description="An api key, as: `Token <api key>`."
                )
            },
        ),
    )


def openapi_json() -> str:
    """
    The Smarter api's OpenAPI document, as the text of ``openapi.json``.

    :returns: The document, as indented JSON, with a final newline.
    :rtype: str
    """
    document = openapi_document().model_dump(mode="json")
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def write_openapi(path: str = OPENAPI_PATH) -> str:
    """
    Write the Smarter api's OpenAPI document.

    :param path: The file to write. Defaults to ``openapi.json``, beside this module.
    :type path: str
    :returns: The path that was written.
    :rtype: str
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(openapi_json())
    return path


__all__ = ["openapi_document", "openapi_json", "write_openapi"]
