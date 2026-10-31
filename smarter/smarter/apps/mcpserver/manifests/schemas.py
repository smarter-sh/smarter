"""
The SAM manifests of this platform, as the Smarter Project MCP server's ``get_manifest_schema`` tool reads them.

Each resource kind's JSON Schema and example manifest are committed in
:mod:`smarter.apps.api.v1.contract.sam`, beside the api contract, as
``sam/<Kind>.schema.json`` and ``sam/<Kind>.example.json``. They are the platform's own,
so they describe exactly the manifests that this platform accepts.

A schema is too large, up to about 50 KB, and too nested, with ``$ref`` and ``anyOf``, for
an LLM to read well. :func:`manifest_fields` flattens it into one :class:`ManifestField`
per field, with its dotted path, e.g. ``spec.config.value``, its type, whether it is
required, its default and its description. The read-only ``status`` is left out: it is
never written in a manifest.

:func:`validate_manifest_text` parses a manifest that the LLM wrote, and validates it with
:func:`smarter.apps.api.v1.cli.validation.validate_manifest`, the validation of the cli's
``validate`` command, for the ``validate_manifest`` tool. The text comes from anonymous
clients, so it is parsed without YAML aliases, whose expansion could make a small document
enormous, and it is validated without the checks that make requests, e.g. that an image url
responds.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import glob
import json
import os
import re
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from yaml.composer import ComposerError

from smarter.apps.api.v1.contract.const import (
    SAM_EXAMPLE_SUFFIX,
    SAM_SCHEMA_DIR,
    SAM_SCHEMA_SUFFIX,
)
from smarter.apps.api.v1.contract.models import CliApiValidation
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.lib.typing import SmarterDictType

SAM_SCHEMA_REPOSITORY_PATH = "smarter/smarter/apps/api/v1/contract/sam"
"""The folder of the schemas and examples in the smarter repository."""
READ_ONLY_SECTIONS = frozenset({"status"})
"""Top-level sections of a manifest that the platform writes, and a manifest never contains."""
MAX_DEPTH = 8
MAX_MANIFEST_LENGTH = 50000
"""The maximum length of a manifest that validate_manifest validates."""
MAX_DESCRIPTION_LENGTH = 240
MAX_TYPE_LENGTH = 80
WHITESPACE = re.compile(r"\s+")
DESCRIPTION_PREFIX = re.compile(r"^(?:[A-Za-z_][\w.]*\[\S*?\]+[.:,]?\s*)?(?:(?:Required|Optional)\b[.,:]?\s*)?")
"""The path, type and required flag that many field descriptions start with, e.g.

``LLMClient.spec.config.prompt.appName[str]. Optional.``, which each field already shows.
"""


def field_description(description: str) -> str:
    """
    Return a field's description, without the path, type and required flag that it may start with.

    :param description: The description, from the schema.
    :returns: The rest of it, clipped to :data:`MAX_DESCRIPTION_LENGTH` characters.
    """
    text = DESCRIPTION_PREFIX.sub("", WHITESPACE.sub(" ", description).strip(), count=1)
    return clip(text[:1].upper() + text[1:], MAX_DESCRIPTION_LENGTH)


class ManifestField(BaseModel):
    """One field of a manifest, flattened from its kind's JSON Schema."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(description="The field's dotted path, e.g. spec.config.value. A list's items end with [].")
    type: str = Field(description="The field's type, e.g. string, integer, list of string, or one of: a, b.")
    required: bool = Field(description="Whether a manifest must have the field, when it has its parent.")
    default: Optional[JsonValue] = Field(default=None, description="The field's default, if it has one.")
    description: str = ""


def manifest_kinds(directory: str = SAM_SCHEMA_DIR) -> list[str]:
    """
    Return the kinds that have a committed JSON Schema.

    :param directory: The folder of the schemas.
    :returns: The kinds, sorted, e.g. ``["Account", "ApiConnection", ...]``.
    """
    return sorted(
        os.path.basename(path)[: -len(SAM_SCHEMA_SUFFIX)]
        for path in glob.glob(os.path.join(directory, f"*{SAM_SCHEMA_SUFFIX}"))
    )


def find_kind(name: str, directory: str = SAM_SCHEMA_DIR) -> Optional[str]:
    """
    Return the kind that a name means, ignoring case.

    :param name: e.g. ``llmclient`` or ``LLMClient``.
    :param directory: The folder of the schemas.
    :returns: The kind, e.g. ``LLMClient``, or None.
    """
    wanted = name.strip().lower()
    return next((kind for kind in manifest_kinds(directory) if kind.lower() == wanted), None)


def read_json(path: str) -> SmarterDictType:
    """Return a committed JSON file."""
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def manifest_schema(kind: str, directory: str = SAM_SCHEMA_DIR) -> SmarterDictType:
    """
    Return a kind's JSON Schema.

    :param kind: The kind, e.g. ``Secret``.
    :param directory: The folder of the schemas.
    :returns: The schema.
    :raises FileNotFoundError: If the kind has no schema.
    """
    return read_json(os.path.join(directory, f"{kind}{SAM_SCHEMA_SUFFIX}"))


def manifest_example(kind: str, directory: str = SAM_SCHEMA_DIR) -> SmarterDictType:
    """
    Return a kind's example manifest.

    :param kind: The kind, e.g. ``Secret``.
    :param directory: The folder of the examples.
    :returns: The manifest.
    :raises FileNotFoundError: If the kind has no example.
    """
    return read_json(os.path.join(directory, f"{kind}{SAM_EXAMPLE_SUFFIX}"))


def clip(text: str, length: int) -> str:
    """Return text with its whitespace collapsed, shortened to at most ``length`` characters."""
    text = WHITESPACE.sub(" ", text).strip()
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"


class SchemaFlattener:
    """
    Flatten a JSON Schema into :class:`ManifestField`, resolving its ``$ref``.

    :param schema: The schema, with its ``$defs``.
    """

    def __init__(self, schema: SmarterDictType):
        self.definitions: SmarterDictType = schema.get("$defs", {})
        self.schema = schema
        self.fields: list[ManifestField] = []

    def resolve(self, node: SmarterDictType) -> SmarterDictType:
        """Return the node that a ``$ref`` names, or the node itself."""
        reference = node.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/$defs/"):
            target = self.definitions.get(reference[len("#/$defs/") :], {})
            return {**target, **{key: value for key, value in node.items() if key != "$ref"}}
        return node

    def variants(self, node: SmarterDictType) -> list[SmarterDictType]:
        """Return the non-null variants of a node, resolved: one for a node without ``anyOf``."""
        node = self.resolve(node)
        if "anyOf" not in node:
            return [node]
        return [self.resolve(variant) for variant in node["anyOf"] if variant.get("type") != "null"]

    def type_label(self, node: SmarterDictType) -> str:
        """Return a node's type, in a few words."""
        labels = []
        for variant in self.variants(node):
            if "enum" in variant:
                labels.append("one of: " + ", ".join(str(value) for value in variant["enum"]))
            elif variant.get("type") == "array":
                labels.append("list of " + self.type_label(variant.get("items", {})))
            elif variant.get("type") == "object" and "properties" not in variant:
                values = variant.get("additionalProperties")
                labels.append(
                    "map of string to " + self.type_label(values) if isinstance(values, dict) and values else "object"
                )
            elif "format" in variant:
                labels.append(f"{variant.get('type', 'string')} ({variant['format']})")
            else:
                labels.append(str(variant.get("type") or "any"))
        return clip(" or ".join(dict.fromkeys(labels)) or "any", MAX_TYPE_LENGTH)

    def children(self, node: SmarterDictType) -> tuple[Optional[SmarterDictType], str]:
        """
        Return the object whose properties are a node's children, and the suffix of their parent's path.

        :returns: An object with properties, and ``""`` for an object, ``"[]"`` for a list of
            objects, or ``".<key>"`` for a map of objects. None if the node has no children.
        """
        for variant in self.variants(node):
            if "properties" in variant:
                return variant, ""
            if variant.get("type") == "array":
                items = self.resolve(variant.get("items", {}))
                if "properties" in items:
                    return items, "[]"
            values = variant.get("additionalProperties")
            if isinstance(values, dict):
                values = self.resolve(values)
                if "properties" in values:
                    return values, ".<key>"
        return None, ""

    def walk(self, node: SmarterDictType, prefix: str = "", depth: int = 0) -> None:
        """Append the fields of an object's properties, and of their children."""
        required = set(node.get("required", []))
        for name, prop in node.get("properties", {}).items():
            if not prefix and name in READ_ONLY_SECTIONS:
                continue
            path = f"{prefix}.{name}" if prefix else name
            resolved = self.resolve(prop)
            self.fields.append(
                ManifestField(
                    path=path,
                    type=self.type_label(prop),
                    required=name in required,
                    default=resolved.get("default"),
                    description=field_description(str(resolved.get("description") or "")),
                )
            )
            child, suffix = self.children(prop)
            if child is not None and depth < MAX_DEPTH:
                self.walk(child, path + suffix, depth + 1)

    def flatten(self) -> list[ManifestField]:
        """Return every field of the schema, parents before their children."""
        self.fields = []
        self.walk(self.schema)
        return self.fields


def manifest_fields(schema: SmarterDictType) -> list[ManifestField]:
    """
    Return every field of a manifest, from its kind's JSON Schema, without the read-only ``status``.

    :param schema: The kind's JSON Schema.
    :returns: The fields, parents before their children, in the schema's order.

    **Example usage**::

        fields = manifest_fields(manifest_schema("Secret"))
        fields[-1].path  # 'spec.config.value'
    """
    return SchemaFlattener(schema).flatten()


class NoAliasSafeLoader(yaml.SafeLoader):  # pylint: disable=too-many-ancestors
    """A YAML safe loader that refuses aliases, ``*name``, whose expansion could make a small document enormous."""

    def compose_node(self, parent, index):  # type: ignore[no-untyped-def]
        if self.check_event(yaml.AliasEvent):
            event = self.peek_event()
            raise ComposerError(None, None, "YAML aliases are not allowed in a manifest", event.start_mark)
        return super().compose_node(parent, index)


def parse_manifest(text: str) -> JsonValue:
    """
    Parse a manifest, in YAML or JSON, which YAML includes.

    :param text: The manifest.
    :returns: The parsed manifest.
    :raises SmarterMCPServerToolError: If it is too long, or is not YAML, or has aliases.
    """
    if len(text) > MAX_MANIFEST_LENGTH:
        raise SmarterMCPServerToolError(f"The manifest is longer than {MAX_MANIFEST_LENGTH} characters.")
    try:
        return yaml.load(text, Loader=NoAliasSafeLoader)  # nosec B506: a safe loader
    except yaml.YAMLError as e:
        raise SmarterMCPServerToolError(f"The manifest is not valid YAML: {clip(str(e), 300)}") from e


def validate_manifest_text(text: str) -> CliApiValidation:
    """
    Validate a manifest that the LLM wrote, against the Pydantic model of its kind, without saving it.

    The checks that make requests, e.g. that an image url responds, are skipped.

    :param text: The manifest, in YAML or JSON.
    :returns: Whether it is valid, and its errors.
    :raises SmarterMCPServerToolError: If it is too long, or is not YAML.
    """
    # the brokers import most of the platform's apps. pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.validation import validate_manifest

    return validate_manifest(parse_manifest(text), external_checks=False)


__all__ = [
    "ManifestField",
    "find_kind",
    "manifest_example",
    "manifest_fields",
    "manifest_kinds",
    "manifest_schema",
    "parse_manifest",
    "validate_manifest_text",
]
