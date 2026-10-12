"""
The JSON Schema of the Smarter Chat api contract, generated from its Pydantic models.

``manage.py export_chat_contract_schema`` writes it to ``chat-contract.schema.json``, beside this
module, and a test fails if the committed file is out of date. Smarter Chat keeps a copy of it, from
which it generates its TypeScript types, and against which it validates its test fixtures.
"""

import json

from pydantic.json_schema import models_json_schema

from smarter.common.conf import smarter_settings
from smarter.lib.typing import SmarterDictType

from .const import CHAT_CONTRACT_V2, SCHEMA_PATH
from .models import CONTRACT_MODELS

SCHEMA_ID = f"https://{smarter_settings.root_domain}/schemas/chat-contract.schema.json"


def chat_contract_schema() -> SmarterDictType:
    """
    The contract's JSON Schema (draft 2020-12): one definition, in ``$defs``, per model.

    :returns: The schema.
    :rtype: SmarterDictType
    """
    _, schema = models_json_schema(
        [(model, "validation") for model in CONTRACT_MODELS],
        title="Smarter Chat API contract",
        description=(
            "The requests and responses of the Smarter Chat configuration and prompt apis, versions 1 and "
            f"{CHAT_CONTRACT_V2}. Generated from smarter.apps.prompt.contract.models; do not edit."
        ),
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID, **schema}


def chat_contract_schema_json() -> str:
    """
    The contract's JSON Schema, as the text of ``chat-contract.schema.json``.

    :returns: The schema, as indented JSON, with a final newline.
    :rtype: str
    """
    return json.dumps(chat_contract_schema(), indent=2, sort_keys=True) + "\n"


def write_chat_contract_schema(path: str = SCHEMA_PATH) -> str:
    """
    Write the contract's JSON Schema.

    :param path: The file to write. Defaults to ``chat-contract.schema.json``, beside this module.
    :type path: str
    :returns: The path that was written.
    :rtype: str
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(chat_contract_schema_json())
    return path


__all__ = ["SCHEMA_ID", "chat_contract_schema", "chat_contract_schema_json", "write_chat_contract_schema"]
