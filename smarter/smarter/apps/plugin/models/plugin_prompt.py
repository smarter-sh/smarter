"""PluginPrompt model for storing LLM prompt configuration for Smarter plugins."""

from typing import Union

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from smarter.common.conf import settings_defaults
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import (
    TimestampedModel,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin_meta import PluginMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


class PluginPrompt(TimestampedModel):
    """
    Stores LLM prompt model configuration for a Smarter plugin.

    The ``PluginPrompt`` model defines the prompt settings and LLM interaction parameters for a plugin. Each instance is linked to a :class:`PluginMeta` object, allowing prompt customization on a per-plugin basis. This includes specifying the LLM provider (such as OpenAI), the system role (which sets the context or persona for the LLM), the model to use, temperature for response creativity, and the maximum number of completion tokens.

    By encapsulating these settings, ``PluginPrompt`` enables fine-grained control over how each plugin interacts with the LLM, supporting use cases such as tailoring the assistant's tone, optimizing for cost or accuracy, and enforcing token limits. This model works in conjunction with :class:`PluginSelector` (which determines when a plugin is invoked) and :class:`PluginMeta` (which provides the core plugin metadata).

    Typical scenarios include customizing the system prompt for different plugins, selecting different LLM models for specific tasks, or adjusting temperature and token limits to balance creativity and resource usage.

    See also:

    - :class:`PluginMeta`
    """

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_prompt_plugin")
    provider = models.TextField(
        help_text="The name of the LLM provider for the plugin. Example: 'openai'.",
        null=True,
        blank=True,
        default=settings_defaults.LLM_DEFAULT_PROVIDER,
    )
    system_role = models.TextField(
        help_text="The role of the system in the conversation.",
        null=True,
        blank=True,
        default="You are a helful assistant.",
    )
    model = models.CharField(
        help_text="The model to use for the completion.", max_length=255, default=settings_defaults.LLM_DEFAULT_MODEL
    )
    temperature = models.FloatField(
        help_text="The higher the temperature, the more creative the result.",
        default=settings_defaults.LLM_DEFAULT_TEMPERATURE,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    max_completion_tokens = models.IntegerField(
        help_text="The maximum number of tokens for both input and output.",
        default=settings_defaults.LLM_DEFAULT_MAX_TOKENS,
        validators=[MinValueValidator(0), MaxValueValidator(8192)],
    )

    def __str__(self) -> str:
        return str(self.plugin.name)

    @classmethod
    def get_cached_prompt_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginPrompt", None]:
        """
        Return a single instance of PluginPrompt by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose prompt should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginPrompt instance if found, otherwise None.
        :rtype: Union[PluginPrompt, None]
        """

        @cache_results()
        def prompt_by_plugin_id(plugin_id: int) -> Union["PluginPrompt", None]:
            try:
                retval = cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
                logger.debug(
                    "%s.get_cached_prompt_by_plugin() fetched and cached PluginPrompt for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                return retval
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_prompt_by_plugin: Prompt not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginPrompt not found for plugin_id: {plugin_id}") from e

        if invalidate:
            prompt_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return prompt_by_plugin_id(plugin.id)  # type: ignore[return-value]
