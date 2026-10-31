"""
The tools that read and validate the platform's schemas.

- ``get_manifest_schema``: a resource kind's example manifest, and its fields.
- ``validate_manifest``: a manifest's errors, from the platform's own validation.

See :mod:`smarter.apps.mcpserver.schemas.schemas`.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Optional, cast

import yaml
from pydantic import Field

from smarter.apps.api.v1.contract.const import SAM_SCHEMA_SUFFIX
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.manifests import schemas
from smarter.apps.mcpserver.protocol.tools import (
    MAX_READ_CHARACTERS,
    SmarterProjectTool,
    ToolArguments,
)
from smarter.apps.mcpserver.repositories import ProjectRepository, get_repository
from smarter.common.const import VERSION
from smarter.lib import json


# -----------------------------------------------------------------------------
# get_manifest_schema
# -----------------------------------------------------------------------------
class GetManifestSchemaArguments(ToolArguments):
    """The arguments of get_manifest_schema."""

    kind: Optional[str] = Field(
        default=None,
        max_length=64,
        description="The resource kind, e.g. LLMClient, Guardrail or MCPClient. Omit it to list the kinds.",
    )


class GetManifestSchemaTool(SmarterProjectTool):
    """A resource kind's example manifest, and the fields of its JSON Schema."""

    name = "get_manifest_schema"
    title = "Get manifest schema"
    description = (
        "Return a Smarter resource kind's example manifest, in YAML, and every field that its manifest may "
        "have: its path, type, whether it is required, its default and its description, from the JSON "
        "Schema that this platform validates manifests with. Use it before writing, fixing or explaining a "
        "manifest, rather than guessing its fields. Omit kind to list the kinds."
    )
    arguments_model = GetManifestSchemaArguments
    uses_repository = False

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(GetManifestSchemaArguments, arguments)
        kinds = schemas.manifest_kinds()
        if not arguments.kind:
            return (
                "# Smarter resource kinds\n\nEach kind's manifest is a YAML file with apiVersion, kind, metadata "
                "and spec. Call get_manifest_schema with one of these kinds for its example and fields:\n\n"
                + "\n".join(f"- {kind}" for kind in kinds)
            )
        kind = schemas.find_kind(arguments.kind)
        if kind is None:
            raise SmarterMCPServerToolError(
                f"{arguments.kind} is not a resource kind. It is one of: {', '.join(kinds)}."
            )
        schema = schemas.manifest_schema(kind)
        example = yaml.safe_dump(schemas.manifest_example(kind), sort_keys=False, allow_unicode=True).rstrip()
        schema_url = self.schema_url(kind)
        header = (
            f"# {kind} manifest\n\n{schema.get('description', '')} The example and fields are this platform's, "
            f"version {VERSION.get('__version__', '0.0.0')}. Apply a manifest with `smarter apply -f <file>.yaml`.\n"
            f"Full JSON Schema: {schema_url}\n\n## Example\n\n```yaml\n{example}\n```\n\n## Fields\n\n"
            "The read-only status, which the platform writes, is left out. `[]` is an item of a list, and "
            "`<key>` a key of a map.\n"
        )
        lines, characters, fields = [], len(header), schemas.manifest_fields(schema)
        for number, field in enumerate(fields):
            line = self.format_field(field)
            if characters + len(line) + 1 > MAX_READ_CHARACTERS:
                lines.append(f"\n[{len(fields) - number} more fields: see the full JSON Schema, {schema_url}]")
                break
            lines.append(line)
            characters += len(line) + 1
        return header + "\n".join(lines)

    @staticmethod
    def schema_url(kind: str) -> str:
        """Return the GitHub url of a kind's JSON Schema, in the smarter repository."""
        repository = get_repository("smarter") or ProjectRepository(
            name="smarter", title="the Smarter platform", description="The Smarter platform."
        )
        return repository.file_url(None, f"{schemas.SAM_SCHEMA_REPOSITORY_PATH}/{kind}{SAM_SCHEMA_SUFFIX}")

    @staticmethod
    def format_field(field: schemas.ManifestField) -> str:
        """Return one field, as a Markdown list item."""
        details = [field.type, "required" if field.required else "optional"]
        if field.default is not None:
            details.append(f"default {json.dumps(field.default)}")
        text = f"- `{field.path}` ({', '.join(details)})"
        return f"{text}: {field.description}" if field.description else text


# -----------------------------------------------------------------------------
# validate_manifest
# -----------------------------------------------------------------------------
class ValidateManifestArguments(ToolArguments):
    """The arguments of validate_manifest."""

    manifest: str = Field(
        min_length=1,
        max_length=schemas.MAX_MANIFEST_LENGTH,
        description="The manifest, in YAML or JSON, with apiVersion, kind, metadata and spec.",
    )


class ValidateManifestTool(SmarterProjectTool):
    """Validate a manifest with the platform's own validation, without applying it."""

    name = "validate_manifest"
    title = "Validate manifest"
    description = (
        "Validate a Smarter manifest, in YAML or JSON, against the model of its kind: the validation "
        "that `smarter apply` does first, without applying it. Returns whether it is valid, and each "
        "error with the path of its field. Call it on every manifest that you write or fix, before you "
        "give it to the user, and fix what it reports. Checks that need the network, e.g. that an image "
        "url responds, are skipped."
    )
    arguments_model = ValidateManifestArguments
    uses_repository = False

    def run(self, arguments: ToolArguments) -> str:
        arguments = cast(ValidateManifestArguments, arguments)
        validation = schemas.validate_manifest_text(arguments.manifest)
        if validation.valid:
            return (
                "The manifest is valid. Apply it with `smarter apply -f <file>.yaml`. The platform may still "
                "refuse it for something outside the manifest, e.g. a Secret that it names does not exist."
            )
        errors = "\n".join(
            f"- `{'.'.join(str(part) for part in error.loc) or '(manifest)'}`: {error.message}"
            for error in validation.errors
        )
        return (
            f"The manifest has {len(validation.errors)} errors:\n\n{errors}\n\n"
            "Fix them, and validate it again. get_manifest_schema lists every field of a kind."
        )


__all__ = ["GetManifestSchemaTool", "ValidateManifestTool"]
