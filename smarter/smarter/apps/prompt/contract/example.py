"""
An example JSON of each model of the Smarter Chat api contract, generated from its JSON Schema.

``manage.py export_chat_contract_example`` writes it to ``chat-contract.example.json``, beside this
module, and a test fails if the committed file is out of date. Every example validates against its
model. Each declares all of its model's fields, including the optional ones, so that it shows the
model's complete shape. Its values are placeholders: a string is its field's name, a number is 0, and
a choice is the first one.
"""

import json

from smarter.lib.typing import SmarterDictType

from .const import EXAMPLE_PATH
from .models import CONTRACT_MODELS, SESSION_KEY_PATTERN
from .schema import chat_contract_schema

EXAMPLE_DATE_TIME = "2026-01-01T00:00:00Z"
"""The value of every ``date-time`` field."""

EXAMPLE_SESSION_KEY = "0123456789abcdef" * 4
"""The value of every chat session key: see :data:`~.models.SESSION_KEY_PATTERN`."""

EXAMPLE_JSON_VALUE = "value"
"""The value of every field that is arbitrary JSON: see :data:`~.models.PromptChatApiJson`."""


def _example_value(schema: SmarterDictType, defs: SmarterDictType, name: str) -> object:
    """
    An example of a value of a JSON Schema.

    :param schema: The value's schema.
    :type schema: SmarterDictType
    :param defs: The ``$defs`` of the contract's schema, against which ``$ref`` are resolved.
    :type defs: SmarterDictType
    :param name: The name of the value's field, which is the example of a string.
    :type name: str
    :returns: The example.
    :rtype: object
    """
    if "$ref" in schema:
        return _example_value(defs[schema["$ref"].split("/")[-1]], defs, name)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if schema.get("default") is not None:
        return schema["default"]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            branches = [branch for branch in schema[key] if branch.get("type") != "null"]
            return _example_value(branches[0], defs, name) if branches else None

    value_type = schema.get("type")
    if value_type == "object":
        properties = schema.get("properties", {})
        if properties:
            return {key: _example_value(value, defs, key) for key, value in properties.items()}
        if isinstance(schema.get("additionalProperties"), dict):
            return {"key": _example_value(schema["additionalProperties"], defs, "key")}
        return {}
    if value_type == "array":
        return [_example_value(schema.get("items", {}), defs, name)]
    if value_type == "string":
        if schema.get("format") == "date-time":
            return EXAMPLE_DATE_TIME
        if schema.get("pattern") == SESSION_KEY_PATTERN:
            return EXAMPLE_SESSION_KEY
        return name
    if value_type == "integer":
        return 0
    if value_type == "number":
        return 0.0
    if value_type == "boolean":
        return False
    return EXAMPLE_JSON_VALUE


def chat_contract_example() -> SmarterDictType:
    """
    An example of each of :data:`~smarter.apps.prompt.contract.models.CONTRACT_MODELS`, by the model's name.

    :returns: The examples.
    :rtype: SmarterDictType
    """
    defs = chat_contract_schema()["$defs"]
    return {model.__name__: _example_value(defs[model.__name__], defs, model.__name__) for model in CONTRACT_MODELS}


def chat_contract_example_json() -> str:
    """
    The contract's examples, as the text of ``chat-contract.example.json``.

    :returns: The examples, as indented JSON, with a final newline.
    :rtype: str
    """
    return json.dumps(chat_contract_example(), indent=2, sort_keys=True) + "\n"


def write_chat_contract_example(path: str = EXAMPLE_PATH) -> str:
    """
    Write the contract's examples.

    :param path: The file to write. Defaults to ``chat-contract.example.json``, beside this module.
    :type path: str
    :returns: The path that was written.
    :rtype: str
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(chat_contract_example_json())
    return path


__all__ = ["chat_contract_example", "chat_contract_example_json", "write_chat_contract_example"]
