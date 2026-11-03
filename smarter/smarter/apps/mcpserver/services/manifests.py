"""
The SAM manifests of this platform, as the MCPServer's public ``get_manifest_schema`` tool reads them.

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
from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError
from smarter.lib.typing import SmarterDictType

SAM_SCHEMA_REPOSITORY_PATH = "smarter/smarter/apps/api/v1/contract/sam"
"""The folder of the schemas and examples in the smarter repository, for links to them on GitHub."""

READ_ONLY_SECTIONS = frozenset({"status"})
"""Top-level sections of a manifest that the platform writes, and a manifest never contains."""

MAX_DEPTH = 8
"""How deep :class:`SchemaFlattener` descends into nested objects, a guard against a schema that refers to itself."""

MAX_MANIFEST_LENGTH = 50000
"""The maximum length of a manifest that validate_manifest validates."""

MAX_DESCRIPTION_LENGTH = 240
"""The most characters of a field's description that :func:`field_description` keeps."""

MAX_TYPE_LENGTH = 80
"""The most characters of a field's type that :meth:`SchemaFlattener.type_label` keeps, e.g. of a long enum."""

WHITESPACE = re.compile(r"\s+")
"""A run of whitespace, which :func:`clip` collapses into one space."""

DESCRIPTION_PREFIX = re.compile(r"^(?:[A-Za-z_][\w.]*\[\S*?\]+[.:,]?\s*)?(?:(?:Required|Optional)\b[.,:]?\s*)?")
"""The path, type and required flag that many field descriptions start with, which each field already shows.

For example, ``LLMClient.spec.config.prompt.appName[str]. Optional.``.
"""


def field_description(description: str) -> str:
    """
    Return a field's description, without the path, type and required flag that it may start with.

    The prefix repeats what :class:`ManifestField` shows in its own fields, so removing it
    leaves more of the LLM's context for what the field means.

    :param description: The description, from the schema.
    :returns: The rest of it, capitalized, and clipped to :data:`MAX_DESCRIPTION_LENGTH` characters.
    """
    collapsed = WHITESPACE.sub(" ", description).strip()
    text = DESCRIPTION_PREFIX.sub("", collapsed, count=1)
    capitalized = text[:1].upper() + text[1:]
    return clip(capitalized, MAX_DESCRIPTION_LENGTH)


class ManifestField(BaseModel):
    """
    One field of a manifest, flattened from its kind's JSON Schema.

    :func:`manifest_fields` returns one per field, parents before their children, and the
    ``get_manifest_schema`` tool shows each one as a line of Markdown. The model is frozen.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(description="The field's dotted path, e.g. spec.config.value. A list's items end with [].")
    """The field's dotted path, e.g. ``spec.config.value``.

    A list's items end with ``[]``, and a map's values with ``.<key>``.
    """

    type: str = Field(description="The field's type, e.g. string, integer, list of string, or one of: a, b.")
    """The field's type, in a few words, e.g. ``string``, ``list of string``, or ``one of: a, b``."""

    required: bool = Field(description="Whether a manifest must have the field, when it has its parent.")
    """Whether a manifest must have the field, when it has the field's parent."""

    default: Optional[JsonValue] = Field(default=None, description="The field's default, if it has one.")
    """The field's default, or None if it has none."""

    description: str = ""
    """What the field means, from the schema, without the prefix that :func:`field_description` removes."""


def manifest_kinds(directory: str = SAM_SCHEMA_DIR) -> list[str]:
    """
    Return the kinds that have a committed JSON Schema.

    Side effect: a listing of ``directory``.

    :param directory: The folder of the schemas.
    :returns: The kinds, sorted, e.g. ``["Account", "ApiConnection", ...]``.
    """
    pattern = os.path.join(directory, f"*{SAM_SCHEMA_SUFFIX}")
    kinds = []
    for path in glob.glob(pattern):
        filename = os.path.basename(path)
        kind = filename[: -len(SAM_SCHEMA_SUFFIX)]
        kinds.append(kind)
    return sorted(kinds)


def find_kind(name: str, directory: str = SAM_SCHEMA_DIR) -> Optional[str]:
    """
    Return the kind that a name means, ignoring case.

    :param name: e.g. ``llmclient`` or ``LLMClient``.
    :param directory: The folder of the schemas.
    :returns: The kind, e.g. ``LLMClient``, or None if no kind has that name.
    """
    wanted = name.strip().lower()
    for kind in manifest_kinds(directory):
        if kind.lower() == wanted:
            return kind
    return None


def read_json(path: str) -> SmarterDictType:
    """
    Return a committed JSON file, parsed.

    :param path: The file's path.
    :returns: The file's JSON object.
    :raises FileNotFoundError: If there is no such file.
    """
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
    """
    Return text with its whitespace collapsed, shortened to at most ``length`` characters.

    :param text: The text.
    :param length: The most characters to return.
    :returns: The text, or, if it is longer, its start followed by an ellipsis, ``…``.
    """
    text = WHITESPACE.sub(" ", text).strip()
    if len(text) <= length:
        return text
    start = text[: length - 1].rstrip()
    return start + "…"


class SchemaFlattener:
    """
    Flatten a JSON Schema into :class:`ManifestField`, resolving its ``$ref``.

    Pydantic's JSON Schemas put every nested model in ``$defs``, refer to it with ``$ref``,
    and write an optional field as ``anyOf`` its type and ``null``. The flattener follows the
    references, drops the ``null`` variants, and walks the properties depth first, so that
    each field becomes one :class:`ManifestField` with its dotted path. Use it through
    :func:`manifest_fields`.

    :param schema: The schema, with its ``$defs``.
    """

    def __init__(self, schema: SmarterDictType):
        """
        Prepare to flatten a schema.

        :param schema: The schema, with its ``$defs``.
        """
        self.definitions: SmarterDictType = schema.get("$defs", {})
        self.schema = schema
        self.fields: list[ManifestField] = []

    def resolve(self, node: SmarterDictType) -> SmarterDictType:
        """
        Return the node that a ``$ref`` names, or the node itself.

        The node's own keys, e.g. a ``description`` or ``default`` beside the ``$ref``, override
        the definition's.

        :param node: A node of the schema.
        :returns: The definition merged with the node's other keys, or the node, if it has no
            ``$ref`` to ``$defs``. A reference to a missing definition resolves to the node's
            other keys.
        """
        reference = node.get("$ref")
        if not isinstance(reference, str):
            return node
        if not reference.startswith("#/$defs/"):
            return node
        definition_name = reference[len("#/$defs/") :]
        target = self.definitions.get(definition_name, {})
        resolved = dict(target)
        for key, value in node.items():
            if key != "$ref":
                resolved[key] = value
        return resolved

    def variants(self, node: SmarterDictType) -> list[SmarterDictType]:
        """
        Return the non-null variants of a node, resolved: one for a node without ``anyOf``.

        :param node: A node of the schema.
        :returns: Each variant of its ``anyOf`` that is not ``null``, resolved, or the resolved
            node itself.
        """
        node = self.resolve(node)
        if "anyOf" not in node:
            return [node]
        variants = []
        for variant in node["anyOf"]:
            if variant.get("type") == "null":
                continue
            variants.append(self.resolve(variant))
        return variants

    def type_label(self, node: SmarterDictType) -> str:
        """
        Return a node's type, in a few words, e.g. ``list of string`` or ``one of: a, b``.

        Each non-null variant gets a label, and duplicate labels are dropped.

        :param node: A node of the schema.
        :returns: The labels, joined with ``or``, clipped to :data:`MAX_TYPE_LENGTH` characters,
            or ``any`` if the node has no type.
        """
        labels = []
        for variant in self.variants(node):
            variant_type = variant.get("type")
            if "enum" in variant:
                enum_values = [str(value) for value in variant["enum"]]
                labels.append("one of: " + ", ".join(enum_values))
            elif variant_type == "array":
                items = variant.get("items", {})
                labels.append("list of " + self.type_label(items))
            elif variant_type == "object" and "properties" not in variant:
                values = variant.get("additionalProperties")
                if isinstance(values, dict) and values:
                    labels.append("map of string to " + self.type_label(values))
                else:
                    labels.append("object")
            elif "format" in variant:
                base_type = variant.get("type", "string")
                labels.append(f"{base_type} ({variant['format']})")
            elif variant_type:
                labels.append(str(variant_type))
            else:
                labels.append("any")
        unique_labels = list(dict.fromkeys(labels))
        label = " or ".join(unique_labels)
        if not label:
            label = "any"
        return clip(label, MAX_TYPE_LENGTH)

    def children(self, node: SmarterDictType) -> tuple[Optional[SmarterDictType], str]:
        """
        Return the object whose properties are a node's children, and the suffix of their parent's path.

        :param node: A node of the schema.
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
        """
        Append the fields of an object's properties, and of their children, to :attr:`fields`.

        It calls itself for each property that has children, until :data:`MAX_DEPTH`. At the
        top level, the read-only sections, :data:`READ_ONLY_SECTIONS`, are skipped.

        :param node: An object of the schema, with ``properties``.
        :param prefix: The dotted path of the object, or ``""`` for the manifest itself.
        :param depth: How deep the object is.
        """
        required = set(node.get("required", []))
        for name, prop in node.get("properties", {}).items():
            if not prefix and name in READ_ONLY_SECTIONS:
                continue
            if prefix:
                path = f"{prefix}.{name}"
            else:
                path = name
            resolved = self.resolve(prop)
            raw_description = resolved.get("description")
            if not raw_description:
                raw_description = ""
            field = ManifestField(
                path=path,
                type=self.type_label(prop),
                required=name in required,
                default=resolved.get("default"),
                description=field_description(str(raw_description)),
            )
            self.fields.append(field)
            child, suffix = self.children(prop)
            if child is not None and depth < MAX_DEPTH:
                self.walk(child, path + suffix, depth + 1)

    def flatten(self) -> list[ManifestField]:
        """
        Return every field of the schema, parents before their children.

        :returns: The fields, in the schema's order. Each call starts over.
        """
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
    flattener = SchemaFlattener(schema)
    fields = flattener.flatten()
    return fields


class NoAliasSafeLoader(yaml.SafeLoader):  # pylint: disable=too-many-ancestors
    """
    A YAML safe loader that refuses aliases, ``*name``, whose expansion could make a small document enormous.

    The manifests come from anonymous clients of the MCP server, so a "billion laughs"
    document, a few lines of nested aliases that expand to gigabytes, must be refused before
    it is expanded. A manifest never needs an alias.
    """

    def compose_node(self, parent, index):  # type: ignore[no-untyped-def]
        """
        Compose the next node, unless it is an alias.

        :param parent: The node's parent, from PyYAML.
        :param index: The node's index in its parent, from PyYAML.
        :returns: The composed node.
        :raises ComposerError: If the node is an alias.
        """
        if self.check_event(yaml.AliasEvent):
            event = self.peek_event()
            raise ComposerError(None, None, "YAML aliases are not allowed in a manifest", event.start_mark)
        return super().compose_node(parent, index)


def parse_manifest(text: str) -> JsonValue:
    """
    Parse a manifest, in YAML or JSON, which YAML includes.

    :param text: The manifest.
    :returns: The parsed manifest.
    :raises SmarterMCPServerServiceError: If it is too long, or is not YAML, or has aliases.
    """
    if len(text) > MAX_MANIFEST_LENGTH:
        raise SmarterMCPServerServiceError(f"The manifest is longer than {MAX_MANIFEST_LENGTH} characters.")
    try:
        return yaml.load(text, Loader=NoAliasSafeLoader)  # nosec B506: a safe loader
    except yaml.YAMLError as e:
        raise SmarterMCPServerServiceError(f"The manifest is not valid YAML: {clip(str(e), 300)}") from e


def validate_manifest_text(text: str) -> CliApiValidation:
    """
    Validate a manifest that the LLM wrote, against the Pydantic model of its kind, without saving it.

    The checks that make requests, e.g. that an image url responds, are skipped.

    :param text: The manifest, in YAML or JSON.
    :returns: Whether it is valid, and its errors.
    :raises SmarterMCPServerServiceError: If it is too long, or is not YAML.
    """
    # the brokers import most of the platform's apps. pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.validation import validate_manifest

    manifest = parse_manifest(text)
    validation = validate_manifest(manifest, external_checks=False)
    return validation


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
