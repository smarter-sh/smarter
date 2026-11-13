"""
The document's components: the JSON Schemas of the models that its operations use.

The schemas are generated from the platform's Pydantic models in one pass, so that a model that two families
share is one schema: the SAM models of every kind, the journal and chat contracts, each family's contract
models, and the cli's data. :func:`cli_schemas` adds the schemas that no model has, e.g. a manifest of any kind.
"""

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from smarter.apps.account.contract.models import ACCOUNT_API_MODELS
from smarter.apps.account.data_export import DATA_EXPORT_API_MODELS
from smarter.apps.account.token_usage import TOKEN_USAGE_API_MODELS
from smarter.apps.api.v1.contract.const import JSON_SCHEMA_DIALECT
from smarter.apps.api.v1.contract.models import (
    CLI_API_MODELS,
    CliApiApplied,
    CliApiGet,
    CliApiPrompt,
    CliApiResource,
    CliApiStatus,
    CliApiValidation,
    CliApiVersion,
    CliApiWhoami,
    OpenApiSchema,
    RestApiErrorResponse,
)
from smarter.apps.api.v1.contract.sam import sam_models
from smarter.apps.guardrail.contract.models import GUARDRAIL_API_MODELS
from smarter.apps.llmclient.contract.models import LLMCLIENT_API_MODELS
from smarter.apps.llmhost.contract.models import LLMHOST_API_MODELS
from smarter.apps.llmtool.extension.contract import EXTENSION_API_MODELS
from smarter.apps.mcpclient.contract.models import (
    MCPCLIENT_API_MODELS,
    MCPClientApiStatusError,
)
from smarter.apps.orchestrator.contract.models import ORCHESTRATOR_API_MODELS
from smarter.apps.prompt.contract.history import PROMPT_HISTORY_API_MODELS
from smarter.apps.prompt.contract.models import (
    PromptChatApiConfigRequest,
    PromptChatApiConfigResponse,
    PromptChatApiErrorResponse,
    PromptChatApiProgressEvent,
    PromptChatApiProgressResult,
    PromptChatApiPromptRequest,
    PromptChatApiPromptResponse,
    PromptChatApiProviderRequestResponse,
)
from smarter.apps.provider.contract.models import PROVIDER_API_MODELS
from smarter.apps.proxy.contract.models import PROXY_API_MODELS
from smarter.apps.secret.contract.models import SECRET_API_MODELS
from smarter.apps.vectorsearch.contract.models import VECTORSEARCH_API_MODELS
from smarter.apps.vectorstore.contract.models import VECTORSTORE_API_MODELS
from smarter.lib.journal.contract.models import (
    JOURNAL_API_MODELS,
    SAMJournalApiEnvelope,
    SAMJournalApiErrorResponse,
)

from .builders import REF_TEMPLATE, envelope, ref

CHAT_MODELS: tuple[type[BaseModel], ...] = (
    PromptChatApiConfigRequest,
    PromptChatApiConfigResponse,
    PromptChatApiPromptRequest,
    PromptChatApiPromptResponse,
    PromptChatApiErrorResponse,
    PromptChatApiProgressEvent,
    PromptChatApiProgressResult,
    PromptChatApiProviderRequestResponse,
)
"""The Smarter Chat api contract's models that the chat api's operations use."""


def model_schemas() -> tuple[dict[str, OpenApiSchema], dict[str, str]]:
    """
    The JSON Schemas of the SAM models, the journal contract and the cli's data, as the document's components.

    :returns: The schemas, by name, and the name of each SAM kind's schema, by kind. A kind's schema is
        named after its model, e.g. SAMGuardrail, unless two models share a name.
    :rtype: tuple[dict[str, OpenApiSchema], dict[str, str]]
    """
    kinds = sam_models()
    models: list[type[BaseModel]] = [
        *kinds.values(),
        SAMJournalApiEnvelope,
        SAMJournalApiErrorResponse,
        *CHAT_MODELS,
        *LLMCLIENT_API_MODELS,
        *GUARDRAIL_API_MODELS,
        *SECRET_API_MODELS,
        *MCPCLIENT_API_MODELS,
        *VECTORSTORE_API_MODELS,
        *LLMHOST_API_MODELS,
        *PROVIDER_API_MODELS,
        *PROXY_API_MODELS,
        *ACCOUNT_API_MODELS,
        *PROMPT_HISTORY_API_MODELS,
        *JOURNAL_API_MODELS,
        *ORCHESTRATOR_API_MODELS,
        *VECTORSEARCH_API_MODELS,
        *EXTENSION_API_MODELS,
        *TOKEN_USAGE_API_MODELS,
        *DATA_EXPORT_API_MODELS,
        *CLI_API_MODELS,
    ]
    refs, schema = models_json_schema([(model, "validation") for model in models], ref_template=REF_TEMPLATE)
    prefix = REF_TEMPLATE.format(model="")
    kind_schemas = {kind: str(refs[(model, "validation")]["$ref"])[len(prefix) :] for kind, model in kinds.items()}
    return schema.get("$defs", {}), kind_schemas


def cli_schemas() -> tuple[dict[str, OpenApiSchema], list[str]]:
    """
    Every schema of the document: the models' schemas, a manifest of any kind, and the responses of the commands.

    :returns: The schemas, by name, and the SAM kinds.
    :rtype: tuple[dict[str, OpenApiSchema], list[str]]
    """
    schemas, kind_schemas = model_schemas()
    kinds = list(kind_schemas)
    # The SAM models declare kind as a string, which every kind's schema would accept, so that a
    # manifest would match each schema of SAMManifest's oneOf. Each kind's broker accepts only its
    # own kind, so its schema's kind is a const, which a generated client also types as a literal.
    for kind, name in kind_schemas.items():
        schemas[name]["properties"]["kind"]["const"] = kind  # type: ignore[index,call-overload]
    schemas["SAMManifest"] = {
        "description": "A SAM manifest of any kind. Its kind selects its schema.",
        "oneOf": [ref(name) for name in kind_schemas.values()],
        "discriminator": {
            "propertyName": "kind",
            "mapping": {kind: REF_TEMPLATE.format(model=name) for kind, name in kind_schemas.items()},
        },
    }
    # A list[str] is not a JsonValue, whose lists are invariant list[JsonValue].
    kind_enum: list[OpenApiSchema] = list(kinds)
    schemas["SAMKind"] = {"type": "string", "enum": kind_enum, "description": "A SAM manifest's kind."}
    schemas["JsonSchema"] = {
        "type": "object",
        "description": f"A JSON Schema ({JSON_SCHEMA_DIALECT}).",
        "additionalProperties": True,
    }
    schemas["CliApiApplyResponse"] = envelope(ref(CliApiApplied.__name__), "The response of apply.")
    schemas["CliApiValidateResponse"] = envelope(ref(CliApiValidation.__name__), "The response of validate.")
    schemas["CliApiGetResponse"] = envelope(ref(CliApiGet.__name__), "The response of get.")
    schemas["CliApiManifestResponse"] = envelope(
        ref("SAMManifest"), "A response whose data is a manifest: describe's and example-manifest's."
    )
    schemas["CliApiJsonSchemaResponse"] = envelope(ref("JsonSchema"), "The response of json-schema.")
    schemas["CliApiMessageResponse"] = envelope(None, "A response that has only a message, e.g. delete's.")
    schemas["CliApiStatusResponse"] = envelope(ref(CliApiStatus.__name__), "The response of status.")
    schemas["CliApiVersionResponse"] = envelope(ref(CliApiVersion.__name__), "The response of version.")
    schemas["CliApiWhoamiResponse"] = envelope(ref(CliApiWhoami.__name__), "The response of whoami.")
    schemas["CliApiPromptResponse"] = envelope(ref(CliApiPrompt.__name__), "The response of prompt.")
    schemas["CliApiResourcesResponse"] = envelope(
        {"type": "array", "items": ref(CliApiResource.__name__)}, "The response of resources."
    )
    schemas["CliApiErrorResponse"] = {
        "description": "A journaled error response.",
        "allOf": [ref(SAMJournalApiEnvelope.__name__), ref(SAMJournalApiErrorResponse.__name__)],
    }
    schemas["MCPClientApiErrorResponse"] = {
        "description": "An error: a failed connection to the MCP server, with the MCPClient's connection status, "
        "or another error, e.g. a 404 for an MCPClient that the user may not read.",
        "anyOf": [ref(MCPClientApiStatusError.__name__), ref(RestApiErrorResponse.__name__)],
    }
    schemas["LLMClientPromptErrorResponse"] = {
        "description": "A failed prompt: the prompt's response with its error, whose http status is the LLM "
        "provider's, or, for an error before the prompt runs, e.g. an LLMClient that does not exist, the "
        "chat api's error response.",
        "anyOf": [ref(PromptChatApiPromptResponse.__name__), ref(PromptChatApiErrorResponse.__name__)],
    }
    return schemas, kinds


__all__ = ["CHAT_MODELS", "cli_schemas", "model_schemas"]
