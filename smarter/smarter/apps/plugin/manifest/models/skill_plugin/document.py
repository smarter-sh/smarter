"""
Parsing and validation of ``SKILL.md`` documents, per the Agent Skills specification.

An Agent Skill is a directory containing, at minimum, a ``SKILL.md`` file: a YAML
frontmatter block followed by Markdown instructions. The directory may also contain
bundled files, conventionally in ``scripts/``, ``references/`` and ``assets/``, which
``SKILL.md`` refers to by paths relative to the skill root.

.. code-block:: markdown

    ---
    name: pdf-processing
    description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
    license: Apache-2.0
    allowed-tools: Bash(python:*) Read
    metadata:
      author: example-org
      version: "1.0"
    ---

    # PDF processing

    ## Filling forms
    Read [the forms guide](references/FORMS.md), then run `scripts/fill_form.py`.

This module is shared by the manifest (Pydantic) layer and the storage (Django ORM)
layer, so that both parse and validate ``SKILL.md`` text identically.

.. seealso::

    - Agent Skills specification: https://agentskills.io/specification
    - Anthropic's skills repository: https://github.com/anthropics/skills

.. note::

    **Experimental.** The SkillPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import posixpath
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

from smarter.common.exceptions import SmarterValueError
from smarter.lib import json

SKILL_FILENAME = "SKILL.md"

# frontmatter field constraints, per the Agent Skills specification
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Smarter limits, to bound database rows and LLM context
MAX_SKILL_DOCUMENT_LENGTH = 200_000
"""The maximum length of a SKILL.md document, in characters.

The specification recommends < 500 lines.
"""
MAX_RESOURCE_LENGTH = 500_000
"""The maximum length of a single bundled file, in characters."""
MAX_RESOURCES = 100
"""The maximum number of bundled files."""
MAX_RESOURCE_PATH_LENGTH = 512

# a leading YAML frontmatter block delimited by '---' lines, followed by the Markdown body
FRONTMATTER_PATTERN = re.compile(r"\A---[ \t]*\n(.*?)^---[ \t]*$\n?(.*)\Z", re.DOTALL | re.MULTILINE)

# markdown links, e.g. [the forms guide](references/FORMS.md "title")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
# inline code that looks like a path to a bundled file, e.g. `scripts/fill_form.py`
INLINE_PATH_PATTERN = re.compile(r"`((?:\./)?(?:[\w.-]+/)+[\w.-]+\.\w+|[\w.-]+\.md)`")
URL_SCHEME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


class SkillDocumentError(SmarterValueError):
    """Raised when a SKILL.md document or a bundled file path is invalid."""


@dataclass
class SkillDocument:
    """
    A parsed and validated ``SKILL.md`` document.

    :ivar document: The verbatim SKILL.md text, with line endings normalized to ``\\n``.
    :ivar frontmatter: The complete parsed frontmatter, including any keys beyond the
        standard fields, such as the extensions supported by Claude Code.
    :ivar body: The Markdown instructions that follow the frontmatter.
    :ivar allowed_tools: The ``allowed-tools`` frontmatter field, normalized to a list.
    """

    document: str
    frontmatter: dict[str, Any]
    body: str
    allowed_tools: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        """The skill name."""
        return self.frontmatter["name"]

    @property
    def description(self) -> str:
        """What the skill does and when to use it."""
        return self.frontmatter["description"]

    @property
    def license(self) -> Optional[str]:
        """The license applied to the skill, if any."""
        return self.frontmatter.get("license")

    @property
    def compatibility(self) -> Optional[str]:
        """The environment requirements of the skill, if any."""
        return self.frontmatter.get("compatibility")

    @property
    def metadata(self) -> dict[str, Any]:
        """The ``metadata`` frontmatter field: additional properties not defined by the specification."""
        return self.frontmatter.get("metadata") or {}


def normalize_line_endings(text: str) -> str:
    """Normalize line endings to ``\\n`` and remove a leading byte order mark."""
    return text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")


def parse_allowed_tools(value: Any) -> list[str]:
    """
    Normalize the ``allowed-tools`` frontmatter field to a list of tool names.

    The specification defines ``allowed-tools`` as a space-separated string, e.g.
    ``Bash(git:*) Bash(jq:*) Read``. Tool patterns may themselves contain spaces inside
    parentheses, e.g. ``Bash(git status:*)``. Comma-separated strings and YAML lists,
    both common in practice, are accepted too.

    :param value: The raw frontmatter value.
    :return: The tool names, in order.
    :raises SkillDocumentError: If the value is neither a string nor a list of strings.

    **Example:**

    .. code-block:: python

        parse_allowed_tools("Bash(git status:*) Read, Grep")
        # ['Bash(git status:*)', 'Read', 'Grep']
    """
    if value is None:
        return []
    if isinstance(value, list):
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise SkillDocumentError("frontmatter 'allowed-tools' must be a string or a list of non-empty strings.")
        return [item.strip() for item in value]
    if not isinstance(value, str):
        raise SkillDocumentError("frontmatter 'allowed-tools' must be a space-separated string of tool names.")

    tools: list[str] = []
    current = ""
    depth = 0
    for char in value:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        if depth == 0 and (char.isspace() or char == ","):
            if current:
                tools.append(current)
            current = ""
            continue
        current += char
    if current:
        tools.append(current)
    return tools


def validate_frontmatter(frontmatter: dict[str, Any]) -> None:
    """
    Validate the standard frontmatter fields against the Agent Skills specification.

    Keys beyond the standard fields are permitted and preserved, since agent
    implementations such as Claude Code define their own extensions.

    :param frontmatter: The parsed frontmatter.
    :raises SkillDocumentError: If a standard field is missing or invalid.
    """
    name = frontmatter.get("name")
    if not isinstance(name, str) or not name:
        raise SkillDocumentError("frontmatter 'name' is required.")
    if len(name) > MAX_NAME_LENGTH:
        raise SkillDocumentError(f"frontmatter 'name' must be at most {MAX_NAME_LENGTH} characters: {name}")
    if not NAME_PATTERN.match(name):
        raise SkillDocumentError(
            "frontmatter 'name' may only contain lowercase letters, numbers and hyphens, and must not start "
            f"or end with a hyphen, nor contain consecutive hyphens: {name}"
        )

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        raise SkillDocumentError("frontmatter 'description' is required, and must not be empty.")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise SkillDocumentError(f"frontmatter 'description' must be at most {MAX_DESCRIPTION_LENGTH} characters.")

    license_ = frontmatter.get("license")
    if license_ is not None and not isinstance(license_, str):
        raise SkillDocumentError("frontmatter 'license' must be a string.")

    compatibility = frontmatter.get("compatibility")
    if compatibility is not None:
        if not isinstance(compatibility, str) or not compatibility.strip():
            raise SkillDocumentError("frontmatter 'compatibility' must be a non-empty string.")
        if len(compatibility) > MAX_COMPATIBILITY_LENGTH:
            raise SkillDocumentError(
                f"frontmatter 'compatibility' must be at most {MAX_COMPATIBILITY_LENGTH} characters."
            )

    metadata = frontmatter.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise SkillDocumentError("frontmatter 'metadata' must be a mapping of keys to values.")

    parse_allowed_tools(frontmatter.get("allowed-tools"))


def parse_skill_document(document: str) -> SkillDocument:
    """
    Parse and validate a ``SKILL.md`` document.

    :param document: The verbatim contents of a SKILL.md file.
    :return: The parsed document.
    :raises SkillDocumentError: If the document is too long, has no frontmatter block, the
        frontmatter is not a valid YAML mapping, or a standard frontmatter field is invalid.

    **Example:**

    .. code-block:: python

        skill = parse_skill_document(open("pdf/SKILL.md").read())
        skill.name  # 'pdf'
    """
    if not isinstance(document, str) or not document.strip():
        raise SkillDocumentError("SKILL.md must not be empty.")
    document = normalize_line_endings(document)
    if len(document) > MAX_SKILL_DOCUMENT_LENGTH:
        raise SkillDocumentError(f"SKILL.md must be at most {MAX_SKILL_DOCUMENT_LENGTH} characters.")

    match = FRONTMATTER_PATTERN.match(document)
    if not match:
        raise SkillDocumentError(
            "SKILL.md must begin with a YAML frontmatter block, delimited by '---' lines, that contains "
            "at least 'name' and 'description'."
        )
    raw_frontmatter, body = match.group(1), match.group(2)
    try:
        frontmatter = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError as e:
        raise SkillDocumentError(f"SKILL.md frontmatter is not valid YAML: {e}") from e
    if not isinstance(frontmatter, dict):
        raise SkillDocumentError("SKILL.md frontmatter must be a mapping of keys to values.")

    # YAML can produce values that are not JSON serializable, such as dates.
    frontmatter = json.loads(json.dumps(frontmatter, default=str))
    validate_frontmatter(frontmatter)
    return SkillDocument(
        document=document,
        frontmatter=frontmatter,
        body=body.strip("\n"),
        allowed_tools=parse_allowed_tools(frontmatter.get("allowed-tools")),
    )


def normalize_resource_path(path: str) -> str:
    """
    Normalize the path of a bundled file, relative to the skill root.

    :param path: A relative path, e.g. ``./references/FORMS.md``.
    :return: The normalized path, e.g. ``references/FORMS.md``.
    :raises SkillDocumentError: If the path is empty, absolute, a URL, contains a backslash
        or control characters, or escapes the skill root.
    """
    if not isinstance(path, str) or not path.strip():
        raise SkillDocumentError("resource paths must be non-empty strings.")
    path = path.strip()
    if len(path) > MAX_RESOURCE_PATH_LENGTH:
        raise SkillDocumentError(f"resource paths must be at most {MAX_RESOURCE_PATH_LENGTH} characters: {path}")
    if "\\" in path or any(ord(char) < 32 for char in path):
        raise SkillDocumentError(f"resource paths must not contain backslashes or control characters: {path}")
    if path.startswith("/") or URL_SCHEME_PATTERN.match(path):
        raise SkillDocumentError(f"resource paths must be relative to the skill root: {path}")
    normalized = posixpath.normpath(path)
    if normalized == "." or normalized == ".." or normalized.startswith("../"):
        raise SkillDocumentError(f"resource paths must not refer to files outside of the skill: {path}")
    return normalized


def normalize_resources(resources: Optional[dict[str, Optional[str]]]) -> dict[str, Optional[str]]:
    """
    Validate and normalize a mapping of bundled file paths to their contents.

    A ``None`` value denotes a file whose contents are unavailable, such as a binary asset.

    :param resources: The bundled files, keyed by path relative to the skill root.
    :return: The bundled files, keyed by normalized path, in sorted order.
    :raises SkillDocumentError: If a path is invalid or duplicated after normalization, a
        file is SKILL.md itself, a file is too long, or there are too many files.
    """
    if not resources:
        return {}
    if not isinstance(resources, dict):
        raise SkillDocumentError("resources must be a mapping of relative paths to file contents.")
    if len(resources) > MAX_RESOURCES:
        raise SkillDocumentError(f"a skill may bundle at most {MAX_RESOURCES} files.")
    normalized: dict[str, Optional[str]] = {}
    for path, content in resources.items():
        key = normalize_resource_path(path)
        if key == SKILL_FILENAME:
            raise SkillDocumentError(f"{SKILL_FILENAME} must not be included in resources.")
        if key in normalized:
            raise SkillDocumentError(f"resource path is duplicated: {path}")
        if content is not None:
            if not isinstance(content, str):
                raise SkillDocumentError(f"the contents of resource {path} must be a string.")
            if len(content) > MAX_RESOURCE_LENGTH:
                raise SkillDocumentError(f"resource {path} must be at most {MAX_RESOURCE_LENGTH} characters.")
            content = normalize_line_endings(content)
        normalized[key] = content
    return dict(sorted(normalized.items()))


def find_resource_references(body: str) -> list[str]:
    """
    Find the bundled files that a SKILL.md body refers to.

    Recognizes relative Markdown links, e.g. ``[guide](./reference/guide.md)``, and inline
    code that looks like a path, e.g. ```scripts/fill_form.py```. URLs, absolute paths,
    anchors and paths that escape the skill root are ignored.

    :param body: The Markdown body of a SKILL.md document.
    :return: The normalized paths, without duplicates, in order of first reference.
    """
    candidates = MARKDOWN_LINK_PATTERN.findall(body) + INLINE_PATH_PATTERN.findall(body)
    paths: list[str] = []
    for candidate in candidates:
        candidate = candidate.split("#", 1)[0].split("?", 1)[0]
        if not candidate:
            continue
        try:
            path = normalize_resource_path(candidate)
        except SkillDocumentError:
            continue
        if path != SKILL_FILENAME and path not in paths:
            paths.append(path)
    return paths
