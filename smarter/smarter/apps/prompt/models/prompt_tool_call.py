"""PromptToolCall model for the prompt app."""

from typing import Optional

from django.db import models

from smarter.apps.llmtool.models import PluginMeta
from smarter.lib import json, logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .prompt import Prompt

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


class PromptToolCall(TimestampedModel):
    """Prompt tool call history model."""

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Prompt Tool Call History"

    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE, blank=True, null=True)
    function_name = models.CharField(max_length=255, blank=True, null=True)
    # The tool call's arguments, as the LLM sent them. Unbounded: a web search
    # query or a list of URLs is routinely longer than 255 characters.
    function_args = models.TextField(blank=True, null=True)
    request = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    response = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )

    @classmethod
    def get_cached_object(
        cls, invalidate: Optional[bool] = False, pk: Optional[int] = None, **kwargs
    ) -> Optional["PromptToolCall"]:
        """
        Get the PromptToolCall instance for the given primary key from the cache.

        This method retrieves the PromptToolCall instance associated with the given primary key
        from the cache. If the instance is not found in the cache, it attempts to
        retrieve it from the database. If it still cannot be found, it returns ``None``.

        :param invalidate: Whether to invalidate the cache before retrieving the object.
        :type invalidate: Optional[bool]
        :param pk: The primary key of the PromptToolCall instance to retrieve.
        :type pk: Optional[int]

        :returns: The PromptToolCall instance associated with the given primary key, or ``None`` if not found.
        :rtype: Optional[PromptToolCall]
        """
        cached = super().get_cached_object(invalidate=invalidate, pk=pk, **kwargs)
        return cached if isinstance(cached, cls) else None

    def __str__(self) -> str:
        if self.plugin:
            name = f"{self.prompt.id} - {self.plugin.name}"  # type: ignore[return]
        else:
            name = f"{self.prompt.id} - {self.function_name}"  # type: ignore[return]
        return name
