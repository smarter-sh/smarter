"""PromptHistory model for the prompt app."""

from django.db import models

from smarter.lib import json, logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .prompt import Prompt

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


class PromptHistory(TimestampedModel):
    """Prompt history model."""

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Prompt History"

    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
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
    messages = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )

    def __str__(self) -> str:
        return f"{self.prompt.id}"  # type: ignore[return]

    @property
    def prompt_history(self) -> list[SmarterDictType]:
        """Used by the Reactapp (via PromptConfigView) to display the prompt history."""
        if self.messages:
            return self.messages
        if not self.request:
            return []
        history = self.request.get("messages", [])
        return history
