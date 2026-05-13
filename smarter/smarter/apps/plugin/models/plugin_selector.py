"""
PluginSelector model for defining plugin selection strategies within the Smarter platform.
"""

from typing import Union

from django.db import models
from rest_framework import serializers

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
)
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import (
    TimestampedModel,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin_meta import PluginMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


class PluginSelector(TimestampedModel, SmarterHelperMixin):
    """
    Stores plugin selection strategies for a Smarter plugin.

    The ``PluginSelector`` model defines how and when a plugin is included in the prompt sent to the LLM (Large Language Model). Each instance is linked to a :class:`PluginMeta` object, representing the plugin whose selection logic is being configured.

    The primary function of this model is to specify a selection directive—such as ``search_terms``, ``always``, or ``llm``—that determines the conditions under which the plugin should be activated. For example, when the directive is ``search_terms``, the ``search_terms`` field contains a list of keywords or phrases (in JSON format). If any of these terms are detected in the user's prompt, Smarter will prioritize loading and invoking the associated plugin. This enables context-aware, dynamic plugin routing based on user intent.

    ``PluginSelector`` works in concert with other models in this module:
      - It references :class:`PluginMeta` to associate selection logic with a specific plugin.
      - It is audited by :class:`PluginSelectorHistory`, which records each activation event, the triggering search term, and relevant user prompt context for analytics and debugging.
      - It complements :class:`PluginPrompt`, which customizes the LLM prompt for each plugin, allowing for both selection and prompt configuration to be managed independently.

    By supporting multiple selection strategies, this model enables flexible, intelligent plugin discovery and orchestration within the Smarter platform. It is essential for implementing advanced plugin routing, ensuring that the most relevant plugins are surfaced to the LLM based on user input and system configuration.

    See also:

    - :class:`PluginMeta`
    - :class:`PluginSelectorHistory`
    - :class:`smarter.apps.plugin.manifest.enum.SAMPluginCommonSpecSelectorKeyDirectiveValues`
    """

    SELECT_DIRECTIVES = [
        (
            SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
            SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
        ),
        (
            SAMPluginCommonSpecSelectorKeyDirectiveValues.ALWAYS.value,
            SAMPluginCommonSpecSelectorKeyDirectiveValues.ALWAYS.value,
        ),
        (
            SAMPluginCommonSpecSelectorKeyDirectiveValues.LLM.value,
            SAMPluginCommonSpecSelectorKeyDirectiveValues.LLM.value,
        ),
    ]

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_selector_plugin")
    directive = models.CharField(
        help_text="The selection strategy to use for this plugin.",
        max_length=255,
        default=SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
        choices=SELECT_DIRECTIVES,
    )
    search_terms = models.JSONField(
        help_text="search terms in JSON format that, if detected in the user prompt, will incentivize Smarter to load this plugin.",
        default=list,
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )

    def __str__(self) -> str:
        search_terms = json.dumps(self.search_terms)[:50]
        return f"{str(self.directive)} - {search_terms}"

    @classmethod
    def get_cached_selector_by_plugin(
        cls, plugin: PluginMeta, invalidate: bool = False
    ) -> Union["PluginSelector", None]:
        """
        Return a single instance of PluginSelector by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose selector should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginSelector instance if found, otherwise None.
        :rtype: Union[PluginSelector, None]
        """

        @cache_results()
        def selector_by_plugin_id(plugin_id: int) -> Union["PluginSelector", None]:
            try:
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_selector_by_plugin: Selector not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginSelector with plugin_id {plugin_id} does not exist.") from e

        if invalidate:
            selector_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return selector_by_plugin_id(plugin.id)  # type: ignore[return-value]


class PluginSelectorSerializer(serializers.ModelSerializer):
    """
    Serializer for the PluginSelector model.
    """

    # pylint: disable=C0115
    class Meta:
        model = PluginSelector
        fields = "__all__"
