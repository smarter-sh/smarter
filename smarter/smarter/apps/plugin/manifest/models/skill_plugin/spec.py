"""Smarter API Manifest - Plugin.spec."""

import os
import re
from typing import ClassVar, Optional

import yaml
from pydantic import Field, model_validator

from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBasePydanticModel

from .const import MANIFEST_KIND

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])

# Matches a leading YAML frontmatter block delimited by '---' lines, per the
# SKILL.md convention. Kept identical to the pattern used by
# smarter.apps.plugin.models.plugin_data_skill.PluginDataSkill so that the
# manifest (spec) layer and the storage (ORM) layer parse SKILL.md text
# identically.
FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


class SkillData(SmarterBasePydanticModel):
    """
    Smarter API - generic API Skill data class.

    Models a single SKILL.md-format skill as discrete, validated manifest
    properties: the YAML frontmatter fields (``name``, ``description``,
    ``license``, ``allowed-tools``) plus the Markdown ``instructions`` body
    and any bundled ``resources`` file references.

    ``to_skill_document()`` and ``from_skill_document()`` provide lossless
    round-tripping to/from the canonical SKILL.md text representation
    persisted by ``PluginDataSkill.skill_document``, so a manifest author can
    author a skill either as structured YAML keys under ``skillData``, or by
    pasting a raw SKILL.md file's contents and parsing it with
    ``from_skill_document()``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    name: str = Field(
        ...,
        description=(
            f"{class_identifier}.name[str]: the SKILL.md frontmatter 'name' value. "
            "A short, unique, machine-friendly identifier for this skill."
        ),
    )
    description: str = Field(
        ...,
        description=(
            f"{class_identifier}.description[str]: the SKILL.md frontmatter 'description' value. "
            "A concise summary of what the skill does and when the LLM should use it."
        ),
    )
    license: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.license[str]: the SKILL.md frontmatter 'license' value, if any.",
    )
    allowedTools: Optional[list[str]] = Field(
        default=None,
        description=(
            f"{class_identifier}.allowedTools[list]: the SKILL.md frontmatter 'allowed-tools' value: "
            "the set of tool names this skill is permitted to invoke, if restricted. Omit to allow all tools."
        ),
    )
    instructions: str = Field(
        ...,
        max_length=SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH,
        description=(
            f"{class_identifier}.instructions[str]: the SKILL.md Markdown body: the step-by-step "
            f"instructions returned to the LLM when this skill is invoked. Limited to "
            f"{SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH} characters."
        ),
    )
    resources: Optional[list[str]] = Field(
        default_factory=list,
        description=(
            f"{class_identifier}.resources[list]: optional relative paths to bundled files "
            "(scripts/, references/, assets/) shipped alongside this skill."
        ),
    )

    @model_validator(mode="after")
    def validate_skill_data(self) -> "SkillData":
        """Validate field values beyond what Field()'s declarative constraints already enforce."""
        if not self.name.strip():
            raise SAMValidationError(f"{self.class_identifier}.name must not be empty or whitespace.")
        if not self.description.strip():
            raise SAMValidationError(f"{self.class_identifier}.description must not be empty or whitespace.")
        if not self.instructions.strip():
            raise SAMValidationError(f"{self.class_identifier}.instructions must not be empty or whitespace.")
        if self.allowedTools is not None and (
            not isinstance(self.allowedTools, list)
            or not all(isinstance(tool, str) and tool.strip() for tool in self.allowedTools)
        ):
            raise SAMValidationError(f"{self.class_identifier}.allowedTools must be a list of non-empty strings.")
        if self.resources is not None and (
            not isinstance(self.resources, list)
            or not all(isinstance(resource, str) and resource.strip() for resource in self.resources)
        ):
            raise SAMValidationError(f"{self.class_identifier}.resources must be a list of non-empty strings.")
        return self

    def to_skill_document(self) -> str:
        """
        Render this SkillData as a canonical SKILL.md document: a YAML frontmatter.

        block followed by the Markdown instructions body.

        This is the inverse of :meth:`from_skill_document`, and is the representation
        persisted to :attr:`PluginDataSkill.skill_document` when the manifest controller
        materializes this spec into a Django model instance.

        :return: The rendered SKILL.md text.
        :rtype: str
        """
        frontmatter: dict = {"name": self.name, "description": self.description}
        if self.license:
            frontmatter["license"] = self.license
        if self.allowedTools:
            frontmatter["allowed-tools"] = self.allowedTools

        rendered_frontmatter = yaml.safe_dump(frontmatter, sort_keys=False).strip()
        return f"---\n{rendered_frontmatter}\n---\n\n{self.instructions.strip()}\n"

    @classmethod
    def from_skill_document(cls, skill_document: str) -> "SkillData":
        """
        Parse a raw SKILL.md document (YAML frontmatter + Markdown body) into a.

        validated SkillData instance.

        This is the inverse of :meth:`to_skill_document`, and allows a manifest
        author to paste an existing SKILL.md file's contents directly rather than
        re-authoring it as structured YAML keys.

        :param skill_document: The raw SKILL.md file contents.
        :type skill_document: str
        :return: A validated SkillData instance.
        :rtype: SkillData
        :raises SAMValidationError: If the document has no frontmatter block, the
            frontmatter is not valid YAML, the frontmatter does not parse to a
            mapping, or required keys are missing.
        """
        name: str
        description: str
        license_str: str

        match = FRONTMATTER_PATTERN.match(skill_document or "")
        if not match:
            raise SAMValidationError(
                f"{cls.class_identifier}: skill_document must begin with a YAML frontmatter block "
                "delimited by '---' lines, per the SKILL.md spec."
            )
        raw_frontmatter, body = match.group(1), match.group(2)
        try:
            frontmatter = yaml.safe_load(raw_frontmatter) or {}
            name = frontmatter.get("name")  # type: ignore
            if not name:
                raise SAMValidationError("name is required")
            description = frontmatter.get("description")  # type: ignore
            if not description:
                raise SAMValidationError("description is required")
            license_str = frontmatter.get("license")  # type: ignore
            if not license:
                raise SAMValidationError("license is required")
        except yaml.YAMLError as e:
            raise SAMValidationError(
                f"{cls.class_identifier}: skill_document frontmatter is not valid YAML: {e}"
            ) from e

        if not isinstance(frontmatter, dict):
            raise SAMValidationError(f"{cls.class_identifier}: skill_document frontmatter must parse to a mapping.")

        return cls(
            name=name,
            description=description,
            license=license_str,
            allowedTools=frontmatter.get("allowed-tools"),
            instructions=body.strip(),
        )


class SAMSkillPluginSpec(SAMPluginCommonSpec):
    """Smarter API SkillData Connection Manifest SkillConnection.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    skillData: SkillData = Field(
        ..., description=f"{class_identifier}.selector[obj]: the SkillData to use for the {MANIFEST_KIND}"
    )
