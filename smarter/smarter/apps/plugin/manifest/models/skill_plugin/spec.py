"""
Smarter API Manifest - SkillPlugin.spec.

A SkillPlugin's ``spec.skillData`` contains an Agent Skill, either verbatim or by reference.

**Verbatim:** paste the unmodified contents of a ``SKILL.md`` file into ``skill``, using a
YAML literal block scalar (``|``) so that the Markdown is preserved exactly. Bundled files,
which the skill refers to by relative path, can be pasted into ``resources``.

.. code-block:: yaml

    skillData:
      skill: |
        ---
        name: meeting-notes
        description: Turns raw meeting transcripts into structured notes. Use when the user shares a meeting transcript.
        ---

        # Meeting notes
        Follow the template in [the template](assets/template.md).
      resources:
        assets/template.md: |
          ## Decisions
          ...

**By reference:** refer to a skill in a public GitHub repository, or to any https URL of a
``SKILL.md`` file. The skill and its bundled files are retrieved when the manifest is
applied, and stored with the plugin. Apply the manifest again to retrieve the latest version.

.. code-block:: yaml

    skillData:
      source:
        url: https://github.com/anthropics/skills/tree/main/skills/pdf

.. note::

    **Experimental.** The SkillPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator, model_validator

from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBasePydanticModel

from .const import MANIFEST_KIND
from .document import (
    SkillDocument,
    SkillDocumentError,
    normalize_resources,
    parse_skill_document,
)
from .source import SkillSourceError, SkillSourceLocation, parse_source_url

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


class SkillSource(SmarterBasePydanticModel):
    """Smarter API - SkillPlugin.spec.skillData.source: the remote location of a skill."""

    class_identifier: ClassVar[str] = f"{MODULE_IDENTIFIER}.source"

    url: str = Field(
        ...,
        description=(
            f"{class_identifier}.url[str]: the https URL of the skill. Either a GitHub URL of a skill directory "
            "(e.g. https://github.com/anthropics/skills/tree/main/skills/pdf) or of a SKILL.md file, or any https "
            "URL of a SKILL.md file. The skill and its bundled files are retrieved when the manifest is applied."
        ),
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that the url refers to a supported skill location."""
        try:
            parse_source_url(v)
        except SkillSourceError as e:
            raise SAMValidationError(f"{cls.class_identifier}: {e}") from e
        return v.strip()

    @property
    def location(self) -> SkillSourceLocation:
        """The resolved location of the skill."""
        return parse_source_url(self.url)


class SkillData(SmarterBasePydanticModel):
    """
    Smarter API - SkillPlugin.spec.skillData: an Agent Skill.

    Exactly one of ``skill`` or ``source`` is required.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    skill: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.skill[str]: the verbatim contents of a SKILL.md file: YAML frontmatter, "
            "containing at least 'name' and 'description', followed by Markdown instructions. Use a YAML literal "
            "block scalar (|) to preserve the Markdown exactly. See https://agentskills.io/specification"
        ),
    )
    source: Optional[SkillSource] = Field(
        default=None,
        description=f"{class_identifier}.source[obj]: the remote location of the skill, in lieu of 'skill'.",
    )
    resources: Optional[dict[str, Optional[str]]] = Field(
        default=None,
        description=(
            f"{class_identifier}.resources[obj]: the skill's bundled files, e.g. references/, scripts/ and assets/, "
            "keyed by their path relative to the skill root, as SKILL.md refers to them. Only valid with 'skill'."
        ),
    )

    @model_validator(mode="after")
    def validate_skill_data(self) -> "SkillData":
        """Validate that exactly one of skill or source is provided, and that the skill and its resources are valid."""
        if bool(self.skill) == bool(self.source):
            raise SAMValidationError(f"{self.class_identifier}: exactly one of 'skill' or 'source' is required.")
        if self.source and self.resources:
            raise SAMValidationError(
                f"{self.class_identifier}: 'resources' can only be used with 'skill'. The bundled files of a "
                "remote skill are retrieved from its source."
            )
        try:
            if self.skill:
                parse_skill_document(self.skill)
            normalize_resources(self.resources)
        except SkillDocumentError as e:
            raise SAMValidationError(f"{self.class_identifier}: {e}") from e
        return self

    @property
    def document(self) -> Optional[SkillDocument]:
        """The parsed SKILL.md document of a verbatim skill, or None for a remote skill."""
        return parse_skill_document(self.skill) if self.skill else None


class SAMSkillPluginSpec(SAMPluginCommonSpec):
    """Smarter API Manifest - SkillPlugin.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    skillData: SkillData = Field(
        ...,
        description=f"{class_identifier}.skillData[obj]: the Agent Skill that the {MANIFEST_KIND} provides to the LLM.",
    )
