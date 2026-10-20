"""
The contract of the Prompt Engineer's Workbench's "Architecture" tab: the JSON that it draws, as Pydantic models.

The tab draws an LLMClient's architecture, an :class:`LLMClientArchitecture`: the tree of the SAM resources
that it is built from, which :meth:`smarter.lib.manifest.broker.AbstractBroker.dependency_tree` returns as
:class:`~smarter.lib.manifest.models.SAMDependencyTreeNode`, whether its chat is styled, and the web console
pages where a user browses the Guardrails, tools and api keys that it could use. Beneath the tree, the tab
suggests the next steps for an LLMClient that has no Guardrail, no tools, no styles or no api key. The JSON is camelCase. The
``@smarter/llmclient-architecture`` React package draws it, and the workbench fetches it from
:class:`~smarter.apps.prompt.views.detailviews.prompt_architecture_view.LLMClientArchitectureView` when the
tab is first opened.

``manage.py export_llmclient_architecture_schema`` writes the models' JSON Schema to
``llmclient-architecture.schema.json``, beside this module, from which ``@smarter/llmclient-architecture``
generates its TypeScript types (``make llmclient-architecture-contract``). A test fails if the committed
schema is out of date.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic.json_schema import models_json_schema

from smarter.common.const import SMARTER_PROJECT_WEBSITE_URL
from smarter.lib.manifest.models import SAMDependencyTreeNode
from smarter.lib.typing import SmarterDictType

SCHEMA_PATH = Path(__file__).parent / "llmclient-architecture.schema.json"
"""The committed JSON Schema of the contract."""
SCHEMA_ID = f"{SMARTER_PROJECT_WEBSITE_URL}/schemas/llmclient-architecture.schema.json"


class LLMClientArchitectureModel(BaseModel):
    """The base class of the contract's models: camelCase JSON, and no fields that a model doesn't define."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        # a response always has every field, so the schema, and the TypeScript types generated
        # from it, mark the fields that have defaults as required too.
        json_schema_serialization_defaults_required=True,
    )

    def to_json(self) -> SmarterDictType:
        """The model as the view sends it."""
        return self.model_dump(mode="json")


class LLMClientArchitectureLinks(LLMClientArchitectureModel):
    """The web console's list pages, where a user browses the resources that an LLMClient can add."""

    guardrails_url: str = Field(..., description="The Guardrails page, which lists the built-in Guardrails too.")
    plugins_url: str = Field(..., description="The LLMTools page's Plugins.")
    extensions_url: str = Field(..., description="The LLMTools page's Extensions, which an administrator installs.")
    mcp_clients_url: str = Field(..., description="The MCPClients page.")
    api_keys_url: str = Field(..., description="The API Keys page, which lists the user's api keys.")


class LLMClientArchitecture(LLMClientArchitectureModel):
    """An LLMClient's architecture, as the workbench's Architecture tab draws it.

    ``tree`` is the tree of the SAM resources that the LLMClient is built from, as the user may see it. It
    has no description of its own, which would make the TypeScript generator copy the node's type.
    """

    tree: SAMDependencyTreeNode
    styled: bool = Field(..., description="Whether the LLMClient's manifest styles its chat, in spec.config.styles.")
    links: LLMClientArchitectureLinks


RESPONSE_MODELS: tuple[type[BaseModel], ...] = (LLMClientArchitecture,)
"""What the view sends."""


def contract_schema() -> SmarterDictType:
    """The contract's JSON Schema (draft 2020-12): one definition, in ``$defs``, per model."""
    _, schema = models_json_schema(
        [(model, "serialization") for model in RESPONSE_MODELS],
        title="Smarter LLMClient architecture contract",
        description=(
            "An LLMClient's architecture, which the Prompt Engineer's Workbench draws in its Architecture tab: "
            "the tree of the SAM resources that it is built from, whether its chat is styled, and the web "
            "console pages of the resources that it could add. Generated from "
            "smarter.apps.prompt.views.detailviews.architecture_contract; do not edit."
        ),
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID, **schema}


def contract_schema_json() -> str:
    """The contract's JSON Schema, as the text of ``llmclient-architecture.schema.json``."""
    return json.dumps(contract_schema(), indent=2, sort_keys=True) + "\n"


__all__ = [
    "LLMClientArchitecture",
    "LLMClientArchitectureLinks",
    "LLMClientArchitectureModel",
    "RESPONSE_MODELS",
    "SCHEMA_ID",
    "SCHEMA_PATH",
    "contract_schema",
    "contract_schema_json",
]
