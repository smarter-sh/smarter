"""
The JSON Schema of the Smarter Journal api contract, generated from its Pydantic models.

``manage.py export_journal_contract_schema`` writes it to ``journal-contract.schema.json``, beside
this module, and a test fails if the committed file is out of date.
"""

import json

from pydantic.json_schema import models_json_schema

from smarter.common.const import SMARTER_PROJECT_WEBSITE_URL
from smarter.lib.typing import SmarterDictType

from .const import SCHEMA_PATH
from .models import CONTRACT_MODELS

SCHEMA_ID = f"{SMARTER_PROJECT_WEBSITE_URL}/schemas/journal-contract.schema.json"


def journal_contract_schema() -> SmarterDictType:
    """
    The contract's JSON Schema (draft 2020-12): one definition, in ``$defs``, per model.

    :returns: The schema.
    :rtype: SmarterDictType
    """
    _, schema = models_json_schema(
        [(model, "validation") for model in CONTRACT_MODELS],
        title="Smarter Journal API contract",
        description=(
            "The envelope and error body of the Smarter api's journaled responses, and a journal entry. "
            "Generated from smarter.lib.journal.contract.models; do not edit."
        ),
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID, **schema}


def journal_contract_schema_json() -> str:
    """
    The contract's JSON Schema, as the text of ``journal-contract.schema.json``.

    :returns: The schema, as indented JSON, with a final newline.
    :rtype: str
    """
    return json.dumps(journal_contract_schema(), indent=2, sort_keys=True) + "\n"


def write_journal_contract_schema(path: str = SCHEMA_PATH) -> str:
    """
    Write the contract's JSON Schema.

    :param path: The file to write. Defaults to ``journal-contract.schema.json``, beside this module.
    :type path: str
    :returns: The path that was written.
    :rtype: str
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(journal_contract_schema_json())
    return path


__all__ = ["SCHEMA_ID", "journal_contract_schema", "journal_contract_schema_json", "write_journal_contract_schema"]
