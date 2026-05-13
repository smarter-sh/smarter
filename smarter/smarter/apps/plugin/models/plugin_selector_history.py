"""
PluginSelectorHistory model for tracking plugin selector activations.
"""

from django.db import models
from rest_framework import serializers

from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import json
from smarter.lib.django.models import (
    TimestampedModel,
)

from .plugin_selector import PluginSelector, PluginSelectorSerializer


class PluginSelectorHistory(TimestampedModel, SmarterHelperMixin):
    """
    Stores the history of plugin selector activations for auditing and analytics.

    The ``PluginSelectorHistory`` model records every instance in which a plugin was selected for inclusion in an LLM prompt, capturing the context and rationale for the selection. Each record includes a reference to the associated :class:`PluginSelector`, the specific search term (if any) that triggered the selection, the full set of user prompt messages at the time of activation, and the session key for correlating events across a user session.

    This model is essential for understanding and debugging plugin routing decisions within the Smarter platform. By persisting a detailed log of selector activations, it enables retrospective analysis of plugin usage patterns, supports compliance and auditing requirements, and provides valuable data for improving plugin selection strategies.

    ``PluginSelectorHistory`` works closely with:
      - :class:`PluginSelector`, which defines the selection logic and strategies for plugins.
      - :class:`PluginMeta`, which provides the core metadata for each plugin and is referenced indirectly via the selector.
      - :class:`PluginPrompt`, which may be used to further customize the LLM prompt for the selected plugin.

    Typical use cases include tracking which plugins were surfaced to the LLM in response to specific user queries, analyzing the effectiveness of search term-based selection, and debugging unexpected plugin activations.

    See also:

    - :class:`PluginSelector`
    """

    plugin_selector = models.ForeignKey(
        PluginSelector, on_delete=models.CASCADE, related_name="plugin_selector_history_plugin_selector"
    )
    search_term = models.CharField(max_length=255, blank=True, null=True, default="")
    messages = models.JSONField(
        help_text="The user prompt messages.", default=list, blank=True, null=True, encoder=json.SmarterJSONEncoder
    )
    session_key = models.CharField(max_length=255, blank=True, null=True, default="")

    def __str__(self) -> str:
        return f"{str(self.plugin_selector.plugin.name)} - {self.search_term}"

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Plugin Selector History"


class PluginSelectorHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for the PluginSelectorHistory model.

    This serializer provides a complete representation of :class:`PluginSelectorHistory` records,
    including all model fields and a nested serialization of the related :class:`PluginSelector`.
    It is used to expose selector activation history for auditing, analytics, and debugging purposes.

    By including the nested selector, this serializer enables clients to access both the activation
    context and the selection logic that led to the plugin being surfaced to the LLM. This is
    particularly useful for building admin interfaces, audit logs, or analytics dashboards that
    require insight into plugin routing decisions.

    See also:

    - :class:`PluginSelectorHistory`
    - :class:`PluginSelector`
    """

    plugin_selector = PluginSelectorSerializer()

    # pylint: disable=C0115
    class Meta:
        model = PluginSelectorHistory
        fields = "__all__"
