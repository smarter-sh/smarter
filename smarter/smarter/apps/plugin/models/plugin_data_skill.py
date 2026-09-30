"""
PluginDataSkill model for storing Agent Skill (SKILL.md) plugin data.

.. note::

    **Experimental.** The SkillPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import posixpath
from typing import Any, Optional, Union

from django.db import models

from smarter.apps.account.models.budget import charge_authorization
from smarter.apps.plugin.manifest.models.skill_plugin.document import (
    SkillDocument,
    SkillDocumentError,
    normalize_resource_path,
    normalize_resources,
    parse_skill_document,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin_data_base import PluginDataBase
from .plugin_meta import PluginMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])
logger_prefix = logging.formatted_text(f"{__name__}")


class PluginDataSkill(PluginDataBase):
    """
    Stores an Agent Skill for a Smarter plugin, per the SKILL.md standard.

    An Agent Skill is a ``SKILL.md`` document -- YAML frontmatter (``name``, ``description``,
    and optionally ``license``, ``compatibility``, ``metadata`` and ``allowed-tools``) followed
    by Markdown instructions -- plus any bundled files (``scripts/``, ``references/``,
    ``assets/``) that the instructions refer to by relative path.

    The verbatim ``SKILL.md`` text is stored in ``skill_document``. The parsed frontmatter and
    the normalized ``allowed-tools`` are derived from it on every save. Bundled files are stored
    in ``resources``, keyed by path relative to the skill root.

    Skills that were retrieved from a remote source, such as a GitHub repository, record
    the source URL and retrieval time. Their ``skill_document`` and ``resources`` are a
    snapshot of the remote skill, which is refreshed when the plugin manifest is applied.

    ``PluginDataSkill`` is a concrete subclass of :class:`PluginDataBase`, and is referenced by
    :class:`PluginMeta` to provide the data payload for skill-type plugins.

    .. seealso::

        - :class:`PluginDataBase`
        - :class:`PluginMeta`
        - :py:mod:`smarter.apps.plugin.manifest.models.skill_plugin.document`
        - Agent Skills specification: https://agentskills.io/specification
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
    """The verbatim SKILL.md document (frontmatter + Markdown body)."""

    metadata = models.JSONField(
        help_text="Parsed YAML frontmatter from skill_document (name, description, license, allowed-tools, and any additional custom keys).",
        default=dict,
        encoder=json.SmarterJSONEncoder,
        blank=True,
    )
    """The complete parsed frontmatter of ``skill_document``.

    Derived on every save().
    """

    allowed_tools = models.JSONField(
        help_text="Optional list of tool names this skill is permitted to invoke, mirroring the SKILL.md 'allowed-tools' frontmatter key.",
        default=list,
        encoder=json.SmarterJSONEncoder,
        blank=True,
    )
    """The frontmatter's ``allowed-tools``, normalized to a list.

    Derived on every save().
    """

    resources = models.JSONField(
        help_text=(
            "The skill's bundled files (e.g. scripts/, references/, assets/), keyed by path relative "
            "to the skill root. A null value denotes a file whose contents are unavailable, such as a binary asset."
        ),
        default=dict,
        encoder=json.SmarterJSONEncoder,
        blank=True,
    )
    """The skill's bundled files, keyed by normalized path relative to the skill root."""

    source_url = models.URLField(
        max_length=2048,
        help_text="The URL from which this skill was retrieved, if it was sourced remotely, e.g. from a GitHub repository.",
        blank=True,
        null=True,
    )
    """The skill source URL, as written in the plugin manifest, for remotely sourced skills."""

    source_retrieved_at = models.DateTimeField(
        help_text="When this skill was last retrieved from its source_url.",
        blank=True,
        null=True,
    )
    """When a remotely sourced skill was last retrieved."""

    @property
    def document(self) -> SkillDocument:
        """
        The parsed SKILL.md document.

        :raises SkillDocumentError: If ``skill_document`` is invalid.
        """
        return parse_skill_document(self.skill_document)

    @property
    def instructions(self) -> str:
        """The Markdown instructions of the skill: the body of SKILL.md."""
        return self.document.body

    @property
    def resource_paths(self) -> list[str]:
        """The paths of the skill's bundled files, relative to the skill root."""
        return list(self.resources or {})

    @property
    def return_data_keys(self) -> list[str]:
        """
        Return the paths of the skill's bundled files, which the LLM can request by name.

        :return: The paths of the bundled files, e.g. ``['references/FORMS.md', 'scripts/fill_form.py']``.
        :rtype: list[str]
        """
        return self.resource_paths

    def find_resource(self, path: str) -> tuple[str, Optional[str]]:
        """
        Find a bundled file by the path that the LLM requested.

        The LLM may refer to a file exactly as SKILL.md does, which is not always its actual
        path. For example, Anthropic's pdf skill refers to ``FORMS.md``, which is bundled as
        ``forms.md``. So, in order of precedence, this matches the normalized path, then the
        path ignoring case, then a unique file name ignoring case.

        :param path: The requested path, relative to the skill root.
        :return: A tuple of the file's path and its contents. The contents are None if unavailable.
        :raises SmarterValueError: If no bundled file, or more than one, matches the path.

        **Example:**

        .. code-block:: python

            plugin_data.find_resource("./FORMS.md")
            # ('forms.md', '# PDF form filling guide ...')
        """
        resources = self.resources or {}
        try:
            normalized = normalize_resource_path(path)
        except SkillDocumentError as e:
            raise SmarterValueError(str(e)) from e
        if normalized in resources:
            return normalized, resources[normalized]

        matches = [key for key in resources if key.lower() == normalized.lower()]
        if not matches:
            basename = posixpath.basename(normalized).lower()
            matches = [key for key in resources if posixpath.basename(key).lower() == basename]
        if len(matches) == 1:
            return matches[0], resources[matches[0]]
        if matches:
            raise SmarterValueError(f"resource {path} is ambiguous. It could refer to any of: {sorted(matches)}")
        raise SmarterValueError(f"resource {path} was not found. Available resources are: {self.resource_paths}")

    def validate(self) -> bool:
        """
        Validate the skill document and bundled files.

        :raises SmarterValueError: If ``skill_document`` is not a valid SKILL.md document, or a
            bundled file path or its contents are invalid.
        """
        super().validate()
        parse_skill_document(self.skill_document)
        normalize_resources(self.resources)
        return True

    def save(self, *args, **kwargs):
        """
        Validate the skill, derive the frontmatter fields from ``skill_document``, and save.

        The tool description presented to the LLM defaults to the skill's ``description``,
        which, per the specification, describes what the skill does and when to use it.
        """
        document = parse_skill_document(self.skill_document)
        self.skill_document = document.document
        self.metadata = document.frontmatter
        self.allowed_tools = document.allowed_tools
        self.resources = normalize_resources(self.resources)
        if not self.description:
            self.description = document.description
        super().save(*args, **kwargs)

    def sanitized_return_data(self, params: Optional[dict] = None) -> dict[str, Any]:
        """
        Return the skill, or one of its bundled files, for the LLM.

        This implements the progressive disclosure of the Agent Skills specification. The
        skill's name and description are presented to the LLM as the tool description. When
        the LLM invokes the tool, it receives the skill's instructions, along with the paths
        of its bundled files. The LLM then invokes the tool again, with ``resource`` set to a
        path, to read a bundled file only when the instructions call for it.

        :param params: The tool call arguments. If ``resource`` is present, the bundled file
            at that path is returned instead of the instructions.
        :type params: Optional[dict]
        :return: The skill instructions, or the bundled file.
        :rtype: dict[str, Any]
        :raises SmarterValueError: If the requested resource does not exist.

        **Example:**

        .. code-block:: python

            plugin_data.sanitized_return_data()
            # {'name': 'pdf', 'description': '...', 'instructions': '# PDF processing ...', 'resources': ['forms.md', ...], ...}

            plugin_data.sanitized_return_data({"resource": "forms.md"})
            # {'name': 'pdf', 'resource': 'forms.md', 'content': '# PDF form filling ...'}
        """
        document = self.document
        requested = (params or {}).get("resource")
        if requested:
            path, content = self.find_resource(requested)
            retval: dict[str, Any] = {"name": document.name, "resource": path, "content": content}
            if content is None:
                retval["note"] = "The contents of this file are not available, because it is not a text file."
            return retval

        retval = {
            "name": document.name,
            "description": document.description,
            "instructions": document.body,
        }
        for key, value in (
            ("license", document.license),
            ("compatibility", document.compatibility),
            ("allowed_tools", document.allowed_tools),
            ("metadata", document.metadata),
        ):
            if value:
                retval[key] = value
        if self.resource_paths:
            retval["resources"] = self.resource_paths
            retval["note"] = (
                "The instructions may refer to the bundled files listed in 'resources'. To read one, call this "
                "tool again with 'resource' set to its path. Scripts are provided for reference, and cannot be "
                "executed by this tool."
            )
        return retval

    def data(self, params: Optional[dict] = None) -> Optional[dict]:
        """
        Return the skill as a structured dictionary of frontmatter, instructions and bundled files.

        :param params: Optional parameters for future extensibility (currently unused).
        :type params: Optional[dict]
        :return: A dict with ``frontmatter``, ``instructions`` and ``resources`` keys, or None if
            ``skill_document`` is invalid.
        :rtype: Optional[dict]
        """
        try:
            document = self.document
        except SkillDocumentError as e:
            logger.error("%s.data: Failed to parse skill_document: %s", self.formatted_class_name, e)
            return None
        return {"frontmatter": document.frontmatter, "instructions": document.body, "resources": self.resources}

    def manifest_data(self) -> dict[str, Any]:
        """
        Return the ``spec.skillData`` section of the plugin manifest, as the author wrote it.

        :return: ``{"source": {"url": ...}}`` for a remotely sourced skill, otherwise
            ``{"skill": ..., "resources": ...}``.
        :rtype: dict[str, Any]
        """
        if self.source_url:
            return {"source": {"url": self.source_url}}
        return {"skill": self.skill_document, "resources": self.resources or None}

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
