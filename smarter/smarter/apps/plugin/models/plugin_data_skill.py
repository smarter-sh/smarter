"""PluginDataSkill model for storing SKILL.md-based plugin data configuration."""

import re
from functools import lru_cache
from typing import Any, Optional, Union

import yaml
from django.db import models

from smarter.apps.account.models.budget import charge_authorization
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin_data_base import PluginDataBase
from .plugin_meta import PluginMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])
logger_prefix = logging.formatted_text(f"{__name__}")

# Matches a leading YAML frontmatter block delimited by '---' lines, per the
# SKILL.md convention (https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
# and the broader community "Skill.md" format).
FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)

# Required frontmatter keys per the SKILL.md spec.
REQUIRED_FRONTMATTER_KEYS = ("name", "description")

# Recognized, optional frontmatter keys. Anything else is preserved in `metadata`
# but is not separately validated.
KNOWN_FRONTMATTER_KEYS = REQUIRED_FRONTMATTER_KEYS + ("license", "allowed-tools", "metadata")


class PluginDataSkill(PluginDataBase):
    """
    Stores the configuration and content of a Smarter plugin based on the.

    SKILL.md standard.

    This model is used for plugins that expose a "skill": a self-contained
    Markdown document with a YAML frontmatter header describing the skill
    (``name``, ``description``, and optionally ``license`` and
    ``allowed-tools``), followed by a Markdown body containing the
    instructions the LLM should follow when the skill is invoked. Skills may
    also reference bundled resources (scripts, references, assets) that ship
    alongside the SKILL.md file.

    ``PluginDataSkill`` provides methods for:
      - Parsing ``skill_document`` into its YAML frontmatter and Markdown body.
      - Validating that the frontmatter conforms to the SKILL.md spec (i.e.
        contains the required ``name`` and ``description`` keys).
      - Returning sanitized skill data (name, description, instructions,
        allowed tools, license, and bundled resources) for use in LLM prompts.
      - Extracting and caching the set of top-level keys present in the
        parsed frontmatter.

    This model is a concrete subclass of :class:`PluginDataBase`, and is
    referenced by :class:`PluginMeta` to provide the data payload for
    skill-type plugins. It is also used in conjunction with
    :class:`PluginSelector` and :class:`PluginPrompt` to enable full plugin
    lifecycle management.

    Typical use cases include plugins that teach the LLM a repeatable
    procedure, workflow, or domain-specific technique -- for example, "how to
    fill out this PDF form" or "how to generate a pptx deck" -- without
    requiring a remote API or SQL connection.

    See also:

    - :class:`PluginDataBase`
    - :class:`PluginDataStatic`
    - :class:`PluginDataSql`
    - :class:`PluginMeta`
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Plugin Skill Data"
        verbose_name_plural = "Plugin Skill Data"

    skill_document = models.TextField(
        help_text=(
            "The raw contents of the SKILL.md file for this plugin: a YAML frontmatter "
            "block (name, description, and optionally license and allowed-tools) followed "
            "by a Markdown body containing the instructions returned to the LLM when this "
            "plugin is invoked by the user prompt."
        ),
    )
    """The raw SKILL.md document (frontmatter + Markdown body) that this plugin returns to the LLM."""

    metadata = models.JSONField(
        help_text="Parsed YAML frontmatter from skill_document (name, description, license, allowed-tools, and any additional custom keys).",
        default=dict,
        encoder=json.SmarterJSONEncoder,
        blank=True,
    )
    """Cached, parsed representation of the YAML frontmatter block.

    Repopulated on every save().
    """

    allowed_tools = models.JSONField(
        help_text="Optional list of tool names this skill is permitted to invoke, mirroring the SKILL.md 'allowed-tools' frontmatter key.",
        default=list,
        encoder=json.SmarterJSONEncoder,
        blank=True,
    )
    """Denormalized copy of the frontmatter's `allowed-tools` list, kept in sync on save() for efficient querying."""

    resources = models.JSONField(
        help_text=(
            "Optional list of bundled resource file references (e.g. scripts/, references/, "
            "assets/ paths) that accompany this skill, expressed as relative paths."
        ),
        default=list,
        encoder=json.SmarterJSONEncoder,
        blank=True,
    )
    """Relative paths to any bundled files (scripts, references, assets) shipped alongside this skill."""

    @staticmethod
    def parse_skill_document(skill_document: str) -> tuple[dict[str, Any], str]:
        """
        Split a SKILL.md document into its parsed YAML frontmatter and Markdown body.

        :param skill_document: The raw SKILL.md file contents.
        :type skill_document: str
        :return: A tuple of (frontmatter dict, body markdown string).
        :rtype: tuple[dict[str, Any], str]
        :raises SmarterValueError: If the document has no frontmatter block, or the
            frontmatter is not valid YAML, or does not parse to a dict.
        """
        match = FRONTMATTER_PATTERN.match(skill_document or "")
        if not match:
            raise SmarterValueError(
                "skill_document must begin with a YAML frontmatter block delimited by '---' lines, "
                "per the SKILL.md spec."
            )
        raw_frontmatter, body = match.group(1), match.group(2)
        try:
            frontmatter = yaml.safe_load(raw_frontmatter)
        except yaml.YAMLError as e:
            raise SmarterValueError(f"skill_document frontmatter is not valid YAML: {e}") from e

        if not isinstance(frontmatter, dict):
            raise SmarterValueError("skill_document frontmatter must parse to a mapping of key/value pairs.")

        return frontmatter, body.strip()

    def validate_frontmatter(self) -> dict[str, Any]:
        """
        Validate that ``skill_document`` parses correctly and its frontmatter.

        contains the required SKILL.md keys.

        :return: The parsed frontmatter dict.
        :rtype: dict[str, Any]
        :raises SmarterValueError: If required keys are missing, or ``allowed-tools``
            is present but not a list of strings.
        """
        frontmatter, _ = self.parse_skill_document(self.skill_document)

        missing = [key for key in REQUIRED_FRONTMATTER_KEYS if not frontmatter.get(key)]
        if missing:
            raise SmarterValueError(f"skill_document frontmatter is missing required key(s): {', '.join(missing)}")

        allowed_tools = frontmatter.get("allowed-tools")
        if allowed_tools is not None:
            if not isinstance(allowed_tools, list) or not all(isinstance(item, str) for item in allowed_tools):
                raise SmarterValueError("skill_document frontmatter 'allowed-tools' must be a list of strings.")

        return frontmatter

    def validate(self) -> bool:
        super().validate()
        self.validate_frontmatter()
        return True

    def save(self, *args, **kwargs):
        """Override the save method to parse/validate skill_document and sync derived fields."""
        frontmatter = self.validate_frontmatter()
        self.metadata = frontmatter
        self.allowed_tools = frontmatter.get("allowed-tools") or []
        super().save(*args, **kwargs)
        self.get_cached_data_by_plugin(self.plugin, invalidate=True)

    def sanitized_return_data(self, params: Optional[dict] = None) -> Optional[dict]:
        """
        Return the skill data for this plugin as a dictionary suitable for the LLM.

        This returns the parsed frontmatter fields (``name``, ``description``,
        ``license``, ``allowed-tools``) plus the Markdown instructions body and
        any bundled resource references. The instructions body is truncated to
        ``smarter_settings.plugin_max_data_results`` characters if it exceeds that length,
        to bound prompt size.

        :param params: Optional parameters for future extensibility (currently unused).
        :type params: Optional[dict]
        :return: The sanitized skill data.
        :rtype: Optional[dict]
        :raises SmarterValueError: If skill_document cannot be parsed.
        """
        frontmatter, body = self.parse_skill_document(self.skill_document)

        max_len = getattr(smarter_settings, "plugin_max_data_results", None)
        if isinstance(max_len, int) and max_len > 0 and len(body) > max_len:
            logger.warning(
                "%s.sanitized_return_data: Truncating skill instructions to %s characters.",
                self.formatted_class_name,
                max_len,
            )
            body = body[:max_len]

        return {
            "name": frontmatter.get("name"),
            "description": frontmatter.get("description"),
            "license": frontmatter.get("license"),
            "allowed_tools": frontmatter.get("allowed-tools") or [],
            "instructions": body,
            "resources": self.resources,
        }

    @property
    @lru_cache(maxsize=128)
    def return_data_keys(self) -> Optional[list[str]]:
        """
        Return all top-level keys present in the parsed ``skill_document`` frontmatter.

        :return: A list of frontmatter keys (e.g. ``['name', 'description', 'license']``).
        :rtype: Optional[list[str]]
        :raises SmarterValueError: If skill_document cannot be parsed.

        **Example:**

        .. code-block:: python

            # If skill_document frontmatter is:
            # ---
            # name: pdf-form-filler
            # description: Fill out a PDF form given field values.
            # allowed-tools: [bash, view]
            # ---
            return_data_keys  # ['name', 'description', 'allowed-tools']
        """
        frontmatter, _ = self.parse_skill_document(self.skill_document)
        return list(frontmatter.keys()) if frontmatter else None

    def data(self, params: Optional[dict] = None) -> Optional[dict]:
        """
        Return the skill document as a structured dictionary of frontmatter + instructions.

        Unlike :meth:`sanitized_return_data`, this returns the untruncated body and
        the full, unfiltered frontmatter mapping (including any custom keys beyond
        the standard SKILL.md fields).

        :param params: Optional parameters for future extensibility (currently unused).
        :type params: Optional[dict]
        :return: A dict with ``frontmatter`` and ``instructions`` keys, or None on failure.
        :rtype: Optional[dict]
        """
        try:
            frontmatter, body = self.parse_skill_document(self.skill_document)
            return {"frontmatter": frontmatter, "instructions": body}
        except SmarterValueError as e:
            logger.error("%s.data: Failed to parse skill_document: %s", self.formatted_class_name, e)
            return None

    @classmethod
    def get_cached_data_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginDataSkill", None]:
        """
        Return a single instance of PluginDataSkill by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose data should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginDataSkill instance if found, otherwise None.
        :rtype: Union[PluginDataSkill, None]
        """

        @cache_results()
        def data_by_plugin_id(plugin_id: int) -> Union["PluginDataSkill", None]:
            try:
                retval = cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
                logger.debug(
                    "%s.get_cached_data_by_plugin() fetched and cached PluginDataSkill for plugin_id: %s",
                    logging.formatted_text(cls.__name__),
                    plugin_id,
                )
                return retval
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    logging.formatted_text(cls.__name__),
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataSkill with plugin_id {plugin_id} does not exist.") from e

        if invalidate:
            data_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return data_by_plugin_id(plugin.id)  # type: ignore[return-value]

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        plugin: Optional[PluginMeta] = None,
        **kwargs,
    ) -> Optional["PluginDataBase"]:
        """
        Retrieve a model instance by primary key, using caching to.

        optimize performance. This method is selectively overridden in
        models that inherit from MetaDataModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)

        :param invalidate: If True, invalidate the cache for this query before retrieving the object.
        :type invalidate: bool
        :param pk: The primary key of the model instance to retrieve.
        :type pk: int
        :param plugin: The PluginMeta instance associated with the data to retrieve.
        :type plugin: PluginMeta

        :returns: The model instance if found, otherwise None.
        :rtype: Optional["PluginDataBase"]
        """
        # pylint: disable=W0621
        logger_prefix = logging.formatted_text(f"{__name__}.{PluginDataSkill.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, plugin: %s",
            logger_prefix,
            pk,
            plugin,
        )

        @cache_results()
        def _get_model_by_plugin_meta(plugin_id: int) -> Optional["PluginDataBase"]:
            try:
                logger.debug(
                    "%s._get_model_by_plugin_meta() cache miss for plugin_id: %s",
                    logger_prefix,
                    plugin_id,
                )
                retval = cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
                logger.debug(
                    "%s._get_model_by_plugin_meta() fetched and cached PluginDataSkill for plugin_id: %s",
                    logger_prefix,
                    plugin_id,
                )
                return retval
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataSkill with plugin_id {plugin_id} does not exist.") from e

        if invalidate and plugin:
            _get_model_by_plugin_meta.invalidate(plugin.id)  # type: ignore[union-attr]

        retval: "PluginDataSkill"
        if pk:
            retval = super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]
            charge_authorization(retval.record_locator, cls.__name__)

        if plugin:
            retval = _get_model_by_plugin_meta(plugin.id)  # type: ignore[return-value]
            charge_authorization(retval.record_locator, cls.__name__)

        return retval
