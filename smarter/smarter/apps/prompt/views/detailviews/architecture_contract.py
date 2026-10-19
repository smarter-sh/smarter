"""
The contract of the Prompt Engineer's Workbench's "Architecture" tab: the JSON that it draws, as Pydantic models.

The tab draws an LLMClient's architecture: the tree of the SAM resources that it is built from, which
:meth:`smarter.lib.manifest.broker.AbstractBroker.dependency_tree` returns as
:class:`~smarter.lib.manifest.models.SAMDependencyTreeNode`. The ``@smarter/llmclient-architecture`` React
package draws it, and the workbench fetches it from
:class:`~smarter.apps.prompt.views.detailviews.prompt_architecture_view.LLMClientArchitectureView` when the
tab is first opened.

``manage.py export_llmclient_architecture_schema`` writes the models' JSON Schema to
``llmclient-architecture.schema.json``, beside this module, from which ``@smarter/llmclient-architecture``
generates its TypeScript types (``make llmclient-architecture-contract``). A test fails if the committed
schema is out of date.
"""

import json
from pathlib import Path

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from smarter.common.const import SMARTER_PROJECT_WEBSITE_URL
from smarter.lib.manifest.models import SAMDependencyTreeNode
from smarter.lib.typing import SmarterDictType

SCHEMA_PATH = Path(__file__).parent / "llmclient-architecture.schema.json"
"""The committed JSON Schema of the contract."""
SCHEMA_ID = f"{SMARTER_PROJECT_WEBSITE_URL}/schemas/llmclient-architecture.schema.json"

RESPONSE_MODELS: tuple[type[BaseModel], ...] = (SAMDependencyTreeNode,)
"""What the view sends."""


def contract_schema() -> SmarterDictType:
    """The contract's JSON Schema (draft 2020-12): one definition, in ``$defs``, per model."""
    _, schema = models_json_schema(
        [(model, "serialization") for model in RESPONSE_MODELS],
        title="Smarter LLMClient architecture contract",
        description=(
            "The tree of the SAM resources that an LLMClient is built from, which the Prompt Engineer's "
            "Workbench draws in its Architecture tab. Generated from "
            "smarter.apps.prompt.views.detailviews.architecture_contract; do not edit."
        ),
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID, **schema}


def contract_schema_json() -> str:
    """The contract's JSON Schema, as the text of ``llmclient-architecture.schema.json``."""
    return json.dumps(contract_schema(), indent=2, sort_keys=True) + "\n"


__all__ = [
    "RESPONSE_MODELS",
    "SCHEMA_ID",
    "SCHEMA_PATH",
    "contract_schema",
    "contract_schema_json",
]
