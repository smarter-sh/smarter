"""PromptPluginUsage model for the prompt app."""

from django.db import models

from smarter.apps.plugin.models import PluginMeta
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .prompt import Prompt

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


class PromptPluginUsage(TimestampedModel):
    """Plugin selection history model."""

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Prompt Plugin Usage"

    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)
    input_text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.prompt.id} - {self.plugin.name}"  # type: ignore[return]
