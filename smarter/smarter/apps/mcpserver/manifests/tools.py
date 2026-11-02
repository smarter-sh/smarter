"""
The Smarter Project MCP server's tools that read and validate the platform's manifest schemas.

- ``get_manifest_schema``: a resource kind's example manifest, and its fields.
- ``validate_manifest``: a manifest's errors, from the platform's own validation.

They help an LLM write a correct manifest: it reads a kind's fields before writing one, and
validates what it wrote before giving it to the user. Both work on this platform's own committed
schemas, so they describe the manifests that this platform's version accepts, and neither uses
a repository's index. The schema reading and the validation are in
:mod:`smarter.apps.mcpserver.manifests.schemas`.

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
    """The arguments of ``get_manifest_schema``: the kind, or nothing, to list the kinds."""

    kind: Optional[str] = Field(
        default=None,
        max_length=64,
        description="The resource kind, e.g. LLMClient, Guardrail or MCPClient. Omit it to list the kinds.",
    )


class GetManifestSchemaTool(SmarterProjectTool):
    """
    The ``get_manifest_schema`` tool: a resource kind's example manifest, and the fields of its JSON Schema.

    **Reads:** the committed JSON Schemas and example manifests of
    :mod:`smarter.apps.api.v1.contract.sam`, from the platform's own files.

    **Result:** Markdown. Without a kind, the list of kinds. With one, the kind's description,
    its example manifest in YAML, a link to its full JSON Schema on GitHub, and one line per
    field, as many as fit in :data:`~smarter.apps.mcpserver.protocol.tools.MAX_READ_CHARACTERS`.

    **Side effects:** none. The result is cached like every read-only tool's (see
    :mod:`smarter.apps.mcpserver.caching`).
    """

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
        """
        Describe a kind's manifest, or list the kinds.

        :param arguments: The validated :class:`GetManifestSchemaArguments`.
        :returns: The description, as Markdown.
        :raises SmarterMCPServerToolError: If ``kind`` is not a resource kind.
        """
        arguments = cast(GetManifestSchemaArguments, arguments)
        kinds = schemas.manifest_kinds()
        if not arguments.kind:
            return self.list_kinds(kinds)

        kind = schemas.find_kind(arguments.kind)
        if kind is None:
            kind_list = ", ".join(kinds)
            raise SmarterMCPServerToolError(f"{arguments.kind} is not a resource kind. It is one of: {kind_list}.")

        schema = schemas.manifest_schema(kind)
        example_manifest = schemas.manifest_example(kind)
        example_yaml = yaml.safe_dump(example_manifest, sort_keys=False, allow_unicode=True)
        example = example_yaml.rstrip()
        schema_url = self.schema_url(kind)
        schema_description = schema.get("description", "")
        version = VERSION.get("__version__", "0.0.0")
        header = (
            f"# {kind} manifest\n\n{schema_description} The example and fields are this platform's, "
            f"version {version}. Apply a manifest with `smarter apply -f <file>.yaml`.\n"
            f"Full JSON Schema: {schema_url}\n\n## Example\n\n```yaml\n{example}\n```\n\n## Fields\n\n"
            "The read-only status, which the platform writes, is left out. `[]` is an item of a list, and "
            "`<key>` a key of a map.\n"
        )

        fields = schemas.manifest_fields(schema)
        lines = []
        characters = len(header)
        for number, field in enumerate(fields):
            line = self.format_field(field)
            line_length = len(line) + 1
            if characters + line_length > MAX_READ_CHARACTERS:
                remaining = len(fields) - number
                lines.append(f"\n[{remaining} more fields: see the full JSON Schema, {schema_url}]")
                break
            lines.append(line)
            characters += line_length
        result = header + "\n".join(lines)
        return result

    @staticmethod
    def list_kinds(kinds: list[str]) -> str:
        """
        Return the list of resource kinds, for a call without a kind.

        :param kinds: The kinds, from :func:`~smarter.apps.mcpserver.manifests.schemas.manifest_kinds`.
        :returns: Markdown: a heading, a sentence that says how to use the tool, and one bullet per kind.
        """
        bullets = [f"- {kind}" for kind in kinds]
        intro = (
            "# Smarter resource kinds\n\nEach kind's manifest is a YAML file with apiVersion, kind, metadata "
            "and spec. Call get_manifest_schema with one of these kinds for its example and fields:\n\n"
        )
        result = intro + "\n".join(bullets)
        return result

    @staticmethod
    def schema_url(kind: str) -> str:
        """
        Return the GitHub url of a kind's JSON Schema, in the smarter repository.

        The smarter repository is normally one of
        :data:`~smarter.apps.mcpserver.repositories.SMARTER_PROJECT_REPOSITORIES`. A test may
        replace them, so a stand-in repository with the same name builds the link then.

        :param kind: The kind, e.g. ``Secret``.
        :returns: The url, on the smarter repository's indexed branch.
        """
        repository = get_repository("smarter")
        if repository is None:
            repository = ProjectRepository(
                name="smarter", title="the Smarter platform", description="The Smarter platform."
            )
        path = f"{schemas.SAM_SCHEMA_REPOSITORY_PATH}/{kind}{SAM_SCHEMA_SUFFIX}"
        url = repository.file_url(None, path)
        return url

    @staticmethod
    def format_field(field: schemas.ManifestField) -> str:
        """
        Return one field, as a Markdown list item.

        :param field: The field.
        :returns: e.g. ``- `spec.config.value` (string, required): The secret's value.``
        """
        if field.required:
            requirement = "required"
        else:
            requirement = "optional"
        details = [field.type, requirement]
        if field.default is not None:
            details.append(f"default {json.dumps(field.default)}")
        text = f"- `{field.path}` ({', '.join(details)})"
        if field.description:
            text = f"{text}: {field.description}"
        return text


# -----------------------------------------------------------------------------
# validate_manifest
# -----------------------------------------------------------------------------
class ValidateManifestArguments(ToolArguments):
    """The arguments of ``validate_manifest``: the manifest to validate."""

    manifest: str = Field(
        min_length=1,
        max_length=schemas.MAX_MANIFEST_LENGTH,
        description="The manifest, in YAML or JSON, with apiVersion, kind, metadata and spec.",
    )


class ValidateManifestTool(SmarterProjectTool):
    """
    The ``validate_manifest`` tool: validate a manifest with the platform's own validation, without applying it.

    **Reads:** the manifest that the LLM wrote, which is parsed without YAML aliases and
    validated by :func:`~smarter.apps.mcpserver.manifests.schemas.validate_manifest_text`, the
    validation of the cli's ``validate`` command, without the checks that make requests.

    **Result:** text that says the manifest is valid, or lists each error with the dotted path
    of its field.

    **Side effects:** none: nothing is saved or applied. The result is cached, keyed by the
    manifest, like every read-only tool's (see :mod:`smarter.apps.mcpserver.caching`).
    """

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
        """
        Validate the manifest, and report whether it is valid, or its errors.

        :param arguments: The validated :class:`ValidateManifestArguments`.
        :returns: The report, as text.
        :raises SmarterMCPServerToolError: If the manifest is too long, or is not YAML.
        """
        arguments = cast(ValidateManifestArguments, arguments)
        validation = schemas.validate_manifest_text(arguments.manifest)
        if validation.valid:
            return (
                "The manifest is valid. Apply it with `smarter apply -f <file>.yaml`. The platform may still "
                "refuse it for something outside the manifest, e.g. a Secret that it names does not exist."
            )

        error_lines = []
        for error in validation.errors:
            location_parts = [str(part) for part in error.loc]
            location = ".".join(location_parts)
            if not location:
                location = "(manifest)"
            error_lines.append(f"- `{location}`: {error.message}")
        errors = "\n".join(error_lines)
        result = (
            f"The manifest has {len(validation.errors)} errors:\n\n{errors}\n\n"
            "Fix them, and validate it again. get_manifest_schema lists every field of a kind."
        )
        return result


__all__ = ["GetManifestSchemaTool", "ValidateManifestTool"]
