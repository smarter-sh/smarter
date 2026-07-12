"""
A Plugin that returns a SKILL.md-format skill packaged within the Plugin itself.

.. note::

    This is a complex AI resource that exists within the following class hierarchy

    - Smarter Skill Plugin: The plugin that defines the SKILL.md-format skill (frontmatter + instructions) it exposes to the LLM.
    - Smarter LLMClient: The prompting resource (LLMClient, Agent, Workflow unit, etcetera) that includes the Skill Plugin:

.. sphinx note: these are relative to the rst doc that calls automodule on this file.

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/sample-plugins/pdf-form-filler.yaml
    :language: yaml
    :caption: 1.) Example Skill Plugin Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/llmclient/data/llm-clients/llmclient-example.yaml
    :language: yaml
    :caption: 2.) Example LLMClient Manifest
"""

from datetime import datetime
from typing import Any, Optional, Type, Union

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
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
from smarter.apps.plugin.manifest.models.skill_plugin.model import SAMSkillPlugin
from smarter.apps.plugin.manifest.models.skill_plugin.spec import (
    SAMSkillPluginSpec,
    SkillData,
)
from smarter.apps.plugin.models import PluginDataSkill
from smarter.apps.plugin.serializers import PluginSkillSerializer
from smarter.apps.plugin.signals import plugin_called, plugin_responded
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import settings_defaults
from smarter.lib import json, logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import PluginBase, SmarterPluginError


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SkillPlugin(PluginBase):
    """
    Implements a plugin that returns a SKILL.md-format skill packaged within the plugin itself.

    This class is intended for use cases where the plugin teaches the LLM a repeatable procedure,
    workflow, or domain-specific technique -- expressed as a SKILL.md document (YAML frontmatter
    of ``name``/``description``/``license``/``allowed-tools`` followed by a Markdown instructions
    body) -- rather than returning a data payload or executing a remote query. The skill is exposed
    via the plugin interface and can be invoked through function calls, including those compatible
    with OpenAI's function calling API.

    Typical uses include teaching the LLM how to fill out a PDF form, generate a slide deck, or
    follow some other multi-step, tool-assisted procedure. The plugin supports both manifest-based
    and Django ORM-based initialization for flexible integration.

    **Key Features:**

        - Returns the SKILL.md content (frontmatter fields + instructions body) defined in the plugin manifest or configuration.
        - Integrates with Django ORM for plugin data persistence.
        - Provides a tool definition compatible with OpenAI function calling.
        - Handles serialization and validation of the skill document.
        - Emits signals when the plugin is called and when it responds.

    :param manifest: Optional manifest object for plugin initialization.
    :type manifest: Optional[SAMSkillPlugin]
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    .. note::

        Signals are emitted on plugin call and response for observability and integration.

    .. seealso::

        :class:`PluginBase`
        :class:`PluginDataSkill`
        :class:`PluginSkillSerializer`
        `OpenAI Function Calling Quickstart <https://platform.openai.com/docs/assistants/tools/function-calling/quickstart>`_

    **Example Use Cases:**

        - Teaching an llmclient how to fill out a PDF form given field values.
        - Teaching an llmclient how to assemble a slide deck from a content outline.
        - Providing a repeatable, tool-assisted procedure for a domain-specific task.
    """

    SAMPluginType = SAMSkillPlugin

    _manifest: Optional[SAMSkillPlugin] = None
    _metadata_class: str = SAMPluginCommonMetadataClass.SKILL.value
    _plugin_data: Optional[PluginDataSkill] = None
    _plugin_data_serializer: Optional[PluginSkillSerializer] = None

    def __init__(
        self,
        *args,
        manifest: Optional[SAMSkillPlugin] = None,
        **kwargs,
    ):
        super().__init__(*args, manifest=manifest, **kwargs)

    @property
    def ORMModelClass(self) -> Type[SAMSkillPlugin]:
        """
        Return the Pydantic model class for the SkillPlugin manifest.

        This property provides access to the Pydantic model class that defines the structure
        and validation rules for the SkillPlugin manifest. The returned class is typically
        :class:`SAMSkillPlugin`, which encapsulates all necessary fields and constraints
        for a skill plugin manifest.

        :return: The Pydantic model class for the SkillPlugin manifest.
        :rtype: Type[SAMSkillPlugin]

        Notes
        -----
        This property is useful for introspection, type checking, and for scenarios where
        you need to interact with the manifest model class directly (such as creating new
        instances or performing validation).
        """
        return SAMSkillPlugin

    @property
    def manifest(self) -> Optional[SAMSkillPlugin]:
        """
        Return the Pydantic model representation of the plugin manifest.

        This property provides access to the plugin's manifest as a validated Pydantic model
        (:class:`SAMSkillPlugin`). If the manifest has not been set but the plugin is in a ready state,
        it will attempt to construct the manifest from the current plugin data using the ``to_json()`` method.

        Returns
        -------
        Optional[SAMSkillPlugin]
            The Pydantic model instance representing the plugin manifest, or ``None`` if unavailable.

        Notes
        -----
        This property is useful for accessing structured, validated manifest data regardless of whether
        the plugin was initialized from a manifest or from Django ORM data.
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

        This property provides access to the plugin's data as a Django ORM model instance
        (:class:`PluginDataSkill`). The returned object represents the persistent state of the plugin's
        skill document in the database.

        The property handles several scenarios:

        - If the plugin was initialized from a manifest and is associated with a database record,
          it will construct the ORM instance from the manifest data.
        - If the plugin is already present in the database but not initialized from a manifest,
          it retrieves the existing ORM instance directly.
        - If neither a manifest nor a database record exists, it returns ``None``.

        This property is useful for interacting with the plugin's data using Django's ORM features,
        such as querying, updating, or serializing the skill document.

        Returns
        -------
        Optional[PluginDataSkill]
            The Django ORM instance representing the plugin's skill data, or ``None`` if unavailable.

        Notes
        -----
        This property abstracts the logic for resolving the plugin's data source, ensuring that
        consumers of the property always receive a consistent ORM object when possible.
        """
        if self._plugin_data:
            return self._plugin_data

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
        if self._manifest and self.plugin_meta:
            # this is an update scenario. the Plugin exists in the database,
            # AND we've received manifest data from the cli.
            self._plugin_data = PluginDataSkill(**self.plugin_data_django_model)  # type: ignore[call-arg]
            self._plugin_data.save()
            logger.debug(
                "%s.plugin_data() created new instance of %s from manifest and plugin metadata.",
                self.formatted_class_name,
                self.plugin_data_class.__name__,
            )
        if self.plugin_meta:
            # we don't have a Pydantic model but we do have an existing
            # Django ORM model instance, so we can use that directly.
            logger.debug(
                "%s.plugin_data() retrieving PluginDataSkill from database using plugin metadata.",
                self.formatted_class_name,
            )
            self._plugin_data = PluginDataSkill.get_cached_data_by_plugin(
                plugin=self.plugin_meta,
            )
        # new Plugin scenario. there's nothing in the database yet.
        return self._plugin_data

    @property
    def plugin_data_class(self) -> Type[PluginDataSkill]:
        """
        Return the Django ORM class used for skill plugin data.

        This property provides the class object for the Django model that represents
        the persistent storage of skill plugin data. It is useful for introspection,
        type checking, and for scenarios where you need to interact with the model class
        directly (such as creating new instances, performing queries, or using Django's
        ORM features programmatically).

        The returned class is typically :class:`PluginDataSkill`, which defines the schema
        for storing the SKILL.md document associated with this plugin type.

        :return: The Django ORM class for skill plugin data.
        :rtype: Type[PluginDataSkill]
        """
        return PluginDataSkill

    @property
    def plugin_data_serializer(self) -> Optional[PluginSkillSerializer]:
        """
        Return the serializer instance for the plugin's skill data.

        This property provides a serializer object (:class:`PluginSkillSerializer`) that is
        initialized with the current plugin data. The serializer is responsible for converting
        the Django ORM model instance to and from native Python datatypes, as well as validating
        and serializing the skill document for use in APIs or other interfaces.

        If the serializer has not yet been created, it will be instantiated using the current
        plugin data. This ensures that the serializer always reflects the latest state of the
        plugin's skill data.

        :return: The serializer instance for the plugin's skill data, or ``None`` if the plugin data is unavailable.
        :rtype: Optional[PluginSkillSerializer]

        Notes
        -----
        The serializer is useful for tasks such as rendering the plugin data as JSON, validating
        incoming data, or preparing the data for use in API responses.
        """
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginSkillSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> Type[PluginSkillSerializer]:
        """
        Return the plugin data serializer class.

        This property provides direct access to the serializer class used for skill plugin data.
        The serializer class is responsible for converting Django ORM model instances to and from
        native Python datatypes, as well as validating and serializing the skill document for use in
        APIs or other interfaces.

        Accessing the serializer class is useful when you need to instantiate a new serializer,
        perform type checks, or customize serialization behavior for skill plugin data.

        :return: The serializer class for skill plugin data.
        :rtype: Type[PluginSkillSerializer]

        Notes
        -----
        This property does not return an instance, but rather the class itself, allowing for
        flexible instantiation and extension in advanced use cases.
        """
        return PluginSkillSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """
        Transform the Pydantic model into a Django ORM-compatible dictionary.

        This property generates a dictionary representation of the plugin's skill data,
        suitable for initializing or updating a Django ORM model instance (:class:`PluginDataSkill`).
        The dictionary includes all fields required by the ORM model, namely the plugin reference
        and the rendered SKILL.md document.

        The transformation is performed using the current Pydantic manifest model, if available,
        by rendering ``manifest.spec.skillData`` back into its canonical SKILL.md text via
        :meth:`SkillData.to_skill_document`. This allows for seamless conversion between validated
        manifest data and the persistent database representation used by Django.

        Returns
        -------
        Optional[dict[str, Any]]
            A dictionary containing the fields necessary to create or update a
            :class:`PluginDataSkill` ORM instance, or ``None`` if the manifest is not available.

        Notes
        -----
        This property is useful for bridging the gap between Pydantic-based manifest validation
        and Django ORM persistence, enabling consistent data handling across both systems.
        """
        # recast the Pydantic model to the PluginDataSkill Django ORM model
        if self._manifest:
            skill_data: Optional[SkillData] = (
                self.manifest.spec.skillData
                if self.manifest and self.manifest.spec and self.manifest.spec.skillData
                else None
            )
            return {
                "plugin": self.plugin_meta,
                "skill_document": skill_data.to_skill_document() if skill_data else None,
            }

    @property
    def custom_tool(self) -> Optional[dict[str, Any]]:
        """
        Return the plugin tool definition for OpenAI function calling.

        Unlike a data-lookup plugin, a skill plugin exposes a single procedure: invoking the tool
        returns the entire SKILL.md payload (name, description, license, allowed tools, instructions,
        and bundled resources) for the LLM to follow. No arguments are required to invoke it.

        See the OpenAI documentation:
        https://platform.openai.com/docs/assistants/tools/function-calling/quickstart

        **Example:**

        .. code-block:: python

            tool = {
                "type": "function",
                "function": {
                    "name": "skill_plugin_function",
                    "description": "Fill out a PDF form given a set of field values.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
        """
        if self.ready:
            return {
                "type": "function",
                "function": {
                    "name": self.function_calling_identifier,
                    "description": self.plugin_data.description if self.plugin_data else "Skill Plugin",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
        return None

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        """
        Use Pydantic models to generate an example manifest for a SkillPlugin.

        :param kwargs: Optional keyword arguments to customize the example manifest.
        :type kwargs: Optional[dict[str, Any]]

        :return: An example manifest as a dictionary.
        :rtype: Optional[dict[str, Any]]

        :raises SmarterConfigurationError: If there is an error generating the example manifest.

        See Also:

        - :class:`SAMSkillPlugin`
        - :class:`SmarterApiVersions`
        - :class:`SAMKeys`
        - :class:`SAMMetadataKeys`
        - :class:`SAMPluginCommonMetadataKeys`
        - :class:`SAMPluginCommonMetadataClassValues`
        - :class:`SAMPluginSpecKeys`
        - :class:`SAMPluginCommonSpecSelectorKeys`
        - :class:`SAMPluginCommonSpecSelectorKeyDirectiveValues`
        - :class:`SAMPluginCommonSpecPromptKeys`
        - :class:`SkillData`
        """
        metadata = SAMPluginCommonMetadata(
            name="pdf_form_filler",
            description="Fill out a PDF form given a set of field values, using the pdf skill's fill-form workflow. Use this whenever the user provides a PDF form and asks to have it completed, signed, or populated with data.",
            version="0.1.0",
            tags=["pdf", "forms", "documents"],
            annotations=[
                {"smarter.sh/created_by": "smarter_skill_plugin_broker"},
                {"smarter.sh/plugin": "pdf_form_filler"},
            ],
            pluginClass=SAMPluginCommonMetadataClassValues.SKILL.value,
        )
        selector = SAMPluginCommonSpecSelector(
            directive=SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
            searchTerms=[
                "pdf form",
                "fill out pdf",
                "pdf form filler",
                "complete pdf form",
            ],
        )
        prompt = SAMPluginCommonSpecPrompt(
            provider=settings_defaults.LLM_DEFAULT_PROVIDER,
            systemRole="You are a helpful assistant that fills out PDF forms accurately from the field values the user supplies. Whenever possible you should defer to the tool calls provided for filling and validating PDF form fields.",
            model=settings_defaults.LLM_DEFAULT_MODEL,
            temperature=settings_defaults.LLM_DEFAULT_TEMPERATURE,
            maxTokens=settings_defaults.LLM_DEFAULT_MAX_TOKENS,
        )
        skill_data = SkillData(
            name="pdf-form-filler",
            description="Fill out a PDF form given a set of field values.",
            license="MIT",
            allowedTools=["bash", "view", "str_replace"],
            instructions=(
                "## Filling a PDF form\n\n"
                "1. Inspect the PDF to enumerate its form fields.\n"
                "2. Map each supplied value to its corresponding field name.\n"
                "3. Write the populated values back into the PDF, preserving formatting.\n"
                "4. Flatten the form if the user indicates the result should not be further editable.\n"
            ),
            resources=["scripts/fill_pdf_form.py", "references/pdf_field_types.md"],
        )
        spec = SAMSkillPluginSpec(
            selector=selector,
            prompt=prompt,
            skillData=skill_data,
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

    def tool_call_fetch_plugin_response(self, function_args: dict[str, Any]) -> Union[dict, list, str]:
        """
        Fetch the skill payload from the SkillPlugin when invoked.

        Unlike a data-lookup plugin, invoking a skill plugin does not select among multiple
        stored values; it simply returns the plugin's full sanitized skill payload (name,
        description, license, allowed tools, instructions, and bundled resources) for the LLM
        to follow. ``function_args`` is accepted for interface consistency with other plugin
        types but is not otherwise required to contain any specific keys.

        The method performs several validation steps:

        - Verifies that the plugin is in a ready state and that plugin data is available.
        - Emits signals when the plugin is called and when it responds.
        - Retrieves the plugin's sanitized skill payload.
        - Raises detailed errors if any step fails, including missing plugin data or an
          unexpected return shape.

        Parameters
        ----------
        function_args : dict[str, Any]
            A dictionary of arguments. Accepted for interface consistency with other plugin
            types; no specific keys are required for a skill plugin.

        Returns
        -------
        Union[dict, list, str]
            The sanitized skill payload: a dict containing ``name``, ``description``,
            ``license``, ``allowed_tools``, ``instructions``, and ``resources``.

        Raises
        ------
        SmarterPluginError
            If the plugin is not ready, lacks data, or the sanitized return data is not a
            dictionary.

        Notes
        -----
        This method is typically used as the handler for function calling APIs, enabling
        external systems to retrieve the plugin's skill instructions in a robust and
        validated manner.
        """
        if not isinstance(function_args, dict):
            raise SmarterPluginError(
                f"Plugin {self.name} invalid function_args. Expected a dict, got {type(function_args)}.",
            )

        if not self.ready:
            raise SmarterPluginError(
                f"Plugin {self.name} is not in a ready state.",
            )

        if not self.plugin_data:
            raise SmarterPluginError(
                f"Plugin {self.name} is not ready. Plugin data is not available.",
            )

        plugin_called.send(
            sender=self.tool_call_fetch_plugin_response,
            plugin=self,
            inquiry_type=None,
        )

        try:
            return_data = self.plugin_data.sanitized_return_data(self.params)
            if not isinstance(return_data, dict):
                raise SmarterPluginError(
                    f"Plugin {self.name} return data is not a dictionary.",
                )

            plugin_responded.send(
                sender=self.tool_call_fetch_plugin_response,
                plugin=self,
                inquiry_type=None,
                response=return_data,
            )
            return return_data
        except json.JSONDecodeError as e:
            raise SmarterPluginError(
                f"Plugin {self.name} contains Json data that could not be decoded: {e}.",
            ) from e
