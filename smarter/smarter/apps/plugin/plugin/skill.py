"""
A Plugin that provides an Agent Skill to the LLM, per the SKILL.md standard.

.. note::

    This is a complex AI resource that exists within the following class hierarchy

    1. Smarter Skill Plugin: The plugin that contains, or refers to, an Agent Skill: a SKILL.md document plus any bundled files.
    2. Smarter LLMClient: The prompting resource (LLMClient, Agent, Workflow unit, etcetera) that includes the Skill Plugin.

.. note::

    An Agent Skill is a ``SKILL.md`` document -- YAML frontmatter containing at least ``name``
    and ``description``, followed by Markdown instructions -- plus any bundled files, such as
    ``scripts/``, ``references/`` and ``assets/``, that the instructions refer to by relative path.
    A SkillPlugin manifest either contains the SKILL.md verbatim, or refers to it by URL, such
    as a skill in Anthropic's https://github.com/anthropics/skills repository.

    The SkillPlugin implements the progressive disclosure of the Agent Skills specification:

    1. The skill's ``description`` is the description of the plugin's tool, which tells the
       LLM what the skill does and when to use it.
    2. When the LLM invokes the tool, it receives the skill's instructions and the paths of
       its bundled files.
    3. The LLM invokes the tool again, with a ``resource`` path, to read a bundled file only
       when the instructions call for it.

.. sphinx note: these are relative to the rst doc that calls automodule on this file.

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/sample-plugins/skill-code-review.yaml
    :language: yaml
    :caption: 1.) Example Skill Plugin Manifest, containing a SKILL.md verbatim

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/sample-plugins/skill-anthropic-pdf.yaml
    :language: yaml
    :caption: 2.) Example Skill Plugin Manifest, referring to a skill on GitHub

.. literalinclude:: ../../../../../smarter/smarter/apps/llmclient/data/llm-clients/llmclient-example.yaml
    :language: yaml
    :caption: 3.) Example LLMClient Manifest

.. seealso::

    - Agent Skills specification: https://agentskills.io/specification
    - Anthropic's skills repository: https://github.com/anthropics/skills

.. note::

    **Experimental.** The SkillPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from datetime import datetime
from typing import Any, Optional, Type, Union

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
    SAMPluginSpecKeys,
)
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.spec import (
    SAMPluginCommonSpecPrompt,
    SAMPluginCommonSpecSelector,
)
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.apps.plugin.manifest.models.skill_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.skill_plugin.document import (
    SkillDocumentError,
    normalize_resources,
)
from smarter.apps.plugin.manifest.models.skill_plugin.model import SAMSkillPlugin
from smarter.apps.plugin.manifest.models.skill_plugin.source import SkillSourceError
from smarter.apps.plugin.manifest.models.skill_plugin.spec import (
    SAMSkillPluginSpec,
    SkillData,
)
from smarter.apps.plugin.models import PluginDataSkill
from smarter.apps.plugin.serializers import PluginSkillSerializer
from smarter.apps.plugin.signals import plugin_called, plugin_responded
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import settings_defaults
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys

from .base import PluginBase, SmarterPluginError
from .skill_sources import RetrievedSkill, retrieve_skill


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

RESOURCE_PARAMETER = "resource"

EXAMPLE_SKILL = """---
name: meeting-notes
description: Turns raw meeting transcripts or rough notes into structured meeting notes with a summary, decisions, action items and open questions. Use when the user shares a meeting transcript or rough notes and asks for notes, minutes, a recap or action items.
---

# Meeting notes

## Instructions

1. Read the entire transcript before writing anything.
2. Fill in [the notes template](assets/template.md), section by section.
3. Every action item must have an owner. Never invent an owner. Use "Unassigned" instead.
4. Quote decisions as closely to the attendees' own words as possible.
"""

EXAMPLE_TEMPLATE = """# {Meeting title}

## Summary
## Decisions
## Action items
## Open questions
"""


class SmarterSkillPluginError(SmarterPluginError):
    """Base class for all Skill plugin errors."""


class SkillPlugin(PluginBase):
    """
    Implements a plugin that provides an Agent Skill to the LLM.

    A skill teaches the LLM a repeatable procedure, workflow or domain-specific technique,
    expressed as a ``SKILL.md`` document, rather than returning a data payload or executing
    a remote query. The skill is either contained verbatim in the plugin manifest, or
    retrieved from a remote source, such as a GitHub repository, when the manifest is applied.

    **Key Features:**

        - Accepts an unmodified SKILL.md document, validated against the Agent Skills specification.
        - Accepts a URL of a skill on GitHub, or of any SKILL.md file, in lieu of the document itself.
        - Stores the skill's bundled files, which the LLM can read on demand.
        - Provides a tool definition compatible with OpenAI function calling.
        - Emits signals when the plugin is called and when it responds.

    **Example Use Cases:**

        - Teaching an llmclient a company's code review standards, or brand voice.
        - Teaching an llmclient a database schema and the rules for querying it.
        - Reusing a published skill, such as Anthropic's pdf or mcp-builder skills.

    .. seealso::

        :class:`PluginBase`
        :class:`PluginDataSkill`
        :class:`PluginSkillSerializer`
        :py:mod:`smarter.apps.plugin.plugin.skill_sources`
        `OpenAI Function Calling Quickstart <https://platform.openai.com/docs/assistants/tools/function-calling/quickstart>`_
    """

    SAMPluginType = SAMSkillPlugin

    _manifest: Optional[SAMSkillPlugin] = None
    _metadata_class: str = SAMPluginCommonMetadataClass.SKILL.value
    _plugin_data: Optional[PluginDataSkill] = None
    _plugin_data_serializer: Optional[PluginSkillSerializer] = None
    _retrieved_skill: Optional[RetrievedSkill] = None

    def __init__(
        self,
        *args,
        manifest: Optional[SAMSkillPlugin] = None,
        **kwargs,
    ):
        self._retrieved_skill = None
        super().__init__(*args, manifest=manifest, **kwargs)

    @property
    def kind(self) -> str:
        """
        Returns the kind identifier for this plugin.

        :returns: The string identifier representing the plugin kind.
        :rtype: str

        :example:

            >>> SkillPlugin().kind
            'SkillPlugin'
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSkillPlugin]:
        """
        Return the Pydantic model representation of the plugin manifest.

        If the manifest has not been set but the plugin is in a ready state, it is
        reconstructed from the Django ORM data, using :meth:`to_json`. A remotely sourced
        skill is reconstructed with its ``source``, as the manifest author wrote it.

        :return: The manifest, or ``None`` if unavailable.
        :rtype: Optional[SAMSkillPlugin]
        """
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMSkillPlugin(**self.to_json())  # type: ignore[call-arg]
        return self._manifest

    @property
    def plugin_data(self) -> Optional[PluginDataSkill]:
        """
        Return the plugin data as a Django ORM instance.

        - If the plugin data has already been set, it is returned directly.
        - If the plugin data exists in the database, it is retrieved.
        - If both a manifest and plugin metadata are present, but the plugin data does not
          exist in the database, it is created from the manifest.
        - Otherwise, ``None`` is returned.

        :return: The skill data, or ``None`` if unavailable.
        :rtype: Optional[PluginDataSkill]
        """
        if self._plugin_data:
            return self._plugin_data

        if not self.plugin_meta:
            # new Plugin scenario, or a plugin that is not ready. there's nothing in the database yet.
            return None

        try:
            self._plugin_data = PluginDataSkill.get_cached_object(plugin=self.plugin_meta)  # type: ignore[call-arg]
            logger.debug(
                "%s.plugin_data() retrieved existing PluginDataSkill from database.",
                self.formatted_class_name,
            )
            return self._plugin_data
        except PluginDataSkill.DoesNotExist:
            logger.debug(
                "%s.plugin_data() no existing PluginDataSkill found in database for plugin_meta: %s",
                self.formatted_class_name,
                self.plugin_meta,
            )

        # we only want a preexisting manifest ostensibly sourced
        # from the cli, not a lazy-loaded
        if self._manifest:
            # this is an update scenario. the Plugin exists in the database,
            # AND we've received manifest data from the cli.
            self._plugin_data = PluginDataSkill(**self.plugin_data_django_model)  # type: ignore[call-arg]
            self._plugin_data.save()
            logger.debug(
                "%s.plugin_data() created new instance of %s from manifest and plugin metadata.",
                self.formatted_class_name,
                self.plugin_data_class.__name__,
            )
        return self._plugin_data

    @property
    def plugin_data_class(self) -> Type[PluginDataSkill]:
        """
        Return the Django ORM class used for skill plugin data.

        :return: The Django ORM class for skill plugin data.
        :rtype: Type[PluginDataSkill]
        """
        return PluginDataSkill

    @property
    def plugin_data_serializer(self) -> Optional[PluginSkillSerializer]:
        """
        Return the serializer instance for the plugin's skill data.

        :return: The serializer instance for the plugin's skill data.
        :rtype: Optional[PluginSkillSerializer]
        """
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginSkillSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> Type[PluginSkillSerializer]:
        """
        Return the plugin data serializer class.

        :return: The serializer class for skill plugin data.
        :rtype: Type[PluginSkillSerializer]
        """
        return PluginSkillSerializer

    @property
    def retrieved_skill(self) -> Optional[RetrievedSkill]:
        """
        Return the skill retrieved from the manifest's ``skillData.source``, if any.

        The skill is retrieved once per plugin instance, when it is first needed, which is when
        the manifest is applied. Tool calls use the stored snapshot, and never retrieve it.

        :return: The retrieved skill, or ``None`` if the manifest does not refer to a remote skill.
        :rtype: Optional[RetrievedSkill]
        :raises SmarterSkillPluginError: If the skill cannot be retrieved, or is invalid.
        """
        if self._retrieved_skill:
            return self._retrieved_skill
        source = self._manifest.spec.skillData.source if self._manifest else None
        if not source:
            return None
        try:
            self._retrieved_skill = retrieve_skill(source.url)
        except (SkillSourceError, SkillDocumentError) as e:
            raise SmarterSkillPluginError(
                f"{self.formatted_class_name} {self._manifest.metadata.name} could not retrieve the skill at {source.url}: {e}"  # type: ignore[union-attr]
            ) from e
        return self._retrieved_skill

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """
        Transform the Pydantic manifest into a Django ORM-compatible dictionary.

        A verbatim skill is stored as written. A remotely sourced skill is retrieved, and a
        snapshot of it is stored, along with its source URL and the time it was retrieved.

        The tool description presented to the LLM is the skill's ``description``, which, per
        the specification, describes what the skill does and when to use it.

        :return: A dictionary of :class:`PluginDataSkill` fields, or ``None`` if the manifest is not available.
        :rtype: Optional[dict[str, Any]]
        :raises SmarterSkillPluginError: If a remote skill cannot be retrieved, or is invalid.
        """
        if not self._manifest:
            return None
        skill_data: SkillData = self._manifest.spec.skillData
        retrieved = self.retrieved_skill
        if retrieved:
            document = retrieved.document
            resources = retrieved.resources
            source_url = skill_data.source.url if skill_data.source else None
            source_retrieved_at = retrieved.retrieved_at
        else:
            document = skill_data.document
            resources = normalize_resources(skill_data.resources)
            source_url = None
            source_retrieved_at = None
        if not document:
            raise SmarterSkillPluginError(f"{self.formatted_class_name} {self.name} has no skill.")
        return {
            "plugin": self.plugin_meta,
            "description": document.description,
            "skill_document": document.document,
            "resources": resources,
            "source_url": source_url,
            "source_retrieved_at": source_retrieved_at,
        }

    @property
    def custom_tool(self) -> Optional[dict[str, Any]]:  # type: ignore[override]
        """
        Return the plugin tool definition for OpenAI function calling.

        The tool description is the skill's ``description``. If the skill bundles files, the
        tool takes an optional ``resource`` parameter, whose ``enum`` is the paths of the
        bundled files, so that the LLM can read them on demand.

        See the OpenAI documentation:
        https://platform.openai.com/docs/assistants/tools/function-calling/quickstart

        :return: The tool definition, or ``None`` if the plugin is not ready.
        :rtype: Optional[dict[str, Any]]

        **Example:**

        .. code-block:: python

            tool = {
                "type": "function",
                "function": {
                    "name": "smarter_plugin_0000000042",
                    "description": "Turns raw meeting transcripts into structured meeting notes ...",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "resource": {
                                "type": "string",
                                "description": "Optional. The path of a bundled file to read ...",
                                "enum": ["assets/template.md"],
                            },
                        },
                        "required": [],
                    },
                },
            }
        """
        if not self.ready or not self.plugin_data:
            return None
        properties: dict[str, Any] = {}
        if self.plugin_data.resource_paths:
            properties[RESOURCE_PARAMETER] = {
                "type": "string",
                "description": (
                    "Optional. The path of one of the skill's bundled files to read, as the skill's "
                    "instructions refer to it. Omit this to load the skill's instructions."
                ),
                "enum": self.plugin_data.resource_paths,
            }
        return {
            "type": "function",
            "function": {
                "name": self.function_calling_identifier,
                "description": self.plugin_data.description or self.plugin_data.document.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": [],
                },
            },
        }

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        """
        Use Pydantic models to generate an example manifest for a SkillPlugin.

        :param kwargs: Optional keyword arguments to customize the example manifest.
        :type kwargs: Optional[dict[str, Any]]

        :return: An example manifest as a dictionary.
        :rtype: Optional[dict[str, Any]]

        See Also:

        - :class:`SAMSkillPlugin`
        - :class:`SkillData`
        - ``smarter/apps/plugin/data/sample-plugins/skill-*.yaml`` for more examples.
        """
        metadata = SAMPluginCommonMetadata(
            name="meeting_notes",
            description="Turns raw meeting transcripts into structured notes with decisions and action items.",
            version="0.1.0",
            tags=["productivity", "meetings"],
            annotations=[
                {"smarter.sh/created_by": "smarter_skill_plugin_broker"},
                {"smarter.sh/plugin": "meeting_notes"},
            ],
            pluginClass=SAMPluginCommonMetadataClassValues.SKILL.value,
        )
        selector = SAMPluginCommonSpecSelector(
            directive=SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
            searchTerms=["meeting notes", "meeting transcript", "action items", "minutes"],
        )
        prompt = SAMPluginCommonSpecPrompt(
            provider=settings_defaults.LLM_DEFAULT_PROVIDER,
            systemRole="You are a helpful assistant that produces clear, accurate meeting notes.",
            model=settings_defaults.LLM_DEFAULT_MODEL,
            temperature=settings_defaults.LLM_DEFAULT_TEMPERATURE,
            maxTokens=settings_defaults.LLM_DEFAULT_MAX_TOKENS,
        )
        spec = SAMSkillPluginSpec(
            selector=selector,
            prompt=prompt,
            skillData=SkillData(skill=EXAMPLE_SKILL, resources={"assets/template.md": EXAMPLE_TEMPLATE}),
        )
        status = SAMPluginCommonStatus(
            accountNumber="1234567890",
            username="example_user",
            recordLocator="abc123def456",
            created=datetime(2024, 1, 1, 0, 0, 0),
            modified=datetime(2024, 1, 1, 0, 0, 0),
        )
        sam_skill_plugin = SAMSkillPlugin(
            apiVersion=SmarterApiVersions.V1,
            kind=MANIFEST_KIND,
            metadata=metadata,
            spec=spec,
            status=status,
        )
        return json.loads(sam_skill_plugin.model_dump_json())

    def tool_call_fetch_plugin_response(
        self, function_args: Union[dict[str, Any], str, None]
    ) -> Union[dict, list, str]:
        """
        Return the skill's instructions, or one of its bundled files, in response to a tool call.

        Invoked without arguments, the tool returns the skill's instructions, along with the
        paths of its bundled files. Invoked with ``resource`` set to one of those paths, it
        returns that file. See :meth:`PluginDataSkill.sanitized_return_data`.

        **Example tool call payload:**

        .. code-block:: python

            "tool_calls": [
                {
                    "id": "call_1Ucn2R5WmBh7TtoE197SsP3p",
                    "function": {
                        "arguments": "{\\"resource\\":\\"assets/template.md\\"}",  # these are the function_args
                        "name": "smarter_plugin_0000004468"
                    },
                    "type": "function"
                }
            ]

        :param function_args: The function arguments, as a dict or as the JSON string sent by OpenAI.
        :type function_args: Union[dict[str, Any], str, None]
        :return: The skill's instructions, or the bundled file.
        :rtype: dict
        :raises SmarterSkillPluginError: If the arguments are malformed, the plugin is not ready or
            lacks data, or the requested resource does not exist.
        """
        if isinstance(function_args, str):
            try:
                function_args = json.loads(function_args) if function_args.strip() else {}
            except json.JSONDecodeError as e:
                raise SmarterSkillPluginError(
                    f"Plugin {self.name} function_args is not a valid JSON string: {e}.",
                ) from e
        function_args = function_args or {}
        if not isinstance(function_args, dict):
            raise SmarterSkillPluginError(
                f"Plugin {self.name} function_args must be a dict or a JSON string, got {type(function_args)}.",
            )
        resource = function_args.get(RESOURCE_PARAMETER)
        if resource is not None and not isinstance(resource, str):
            raise SmarterSkillPluginError(
                f"Plugin {self.name} invalid {RESOURCE_PARAMETER}. Expected a string, got {type(resource)}.",
            )

        if not self.ready:
            raise SmarterSkillPluginError(
                f"Plugin {self.name} is not in a ready state.",
            )
        if not self.plugin_data:
            raise SmarterSkillPluginError(
                f"Plugin {self.name} is not ready. Plugin data is not available.",
            )

        plugin_called.send(
            sender=self.tool_call_fetch_plugin_response,
            plugin=self,
            inquiry_type=resource,
        )
        try:
            retval = self.plugin_data.sanitized_return_data({RESOURCE_PARAMETER: resource} if resource else None)
        except SmarterValueError as e:
            raise SmarterSkillPluginError(f"Plugin {self.name}: {e}") from e

        plugin_responded.send(
            sender=self.tool_call_fetch_plugin_response,
            plugin=self,
            inquiry_type=resource,
            response=retval,
        )
        return retval

    def to_json(self, version: str = "v1") -> Optional[dict[str, Any]]:
        """
        Serialize the SkillPlugin to a JSON-compatible dictionary suitable for Pydantic import.

        ``spec.skillData`` is rendered as the manifest author wrote it: ``source`` for a remotely
        sourced skill, otherwise the verbatim ``skill`` and its ``resources``.

        :param version: The API version to use for serialization. Only "v1" is supported.
        :type version: str
        :returns: A dictionary representing the plugin in JSON format, or ``None`` if the plugin is not ready.
        :rtype: Optional[dict[str, Any]]
        :raises SmarterPluginError: If the data is not a valid JSON object, or an unsupported version is specified.
        """
        if not self.ready:
            return None
        if version != "v1":
            raise SmarterPluginError(f"Invalid version: {version}")
        retval = super().to_json(version=version)
        if not isinstance(retval, dict) or not self.plugin_data:
            raise SmarterPluginError(
                f"{self.formatted_class_name}.to_json() error: {self.name} plugin data is not a valid JSON object."
            )
        spec = retval[SAMKeys.SPEC.value]
        spec.pop(SAMPluginSpecKeys.DATA.value, None)
        spec[SAMPluginSpecKeys.SKILL_DATA.value] = self.plugin_data.manifest_data()
        return json.loads(json.dumps(retval))
