"""LLMClientGuardrails model."""

from django.db import models

from smarter.apps.guardrail.models import Guardrail
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .llmclient import LLMClient

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])


class LLMClientGuardrails(TimestampedModel):
    """
    The Guardrails that protect a LLMClient's prompts.

    Each record links an LLMClient to a :class:`~smarter.apps.guardrail.models.Guardrail`, as
    listed in the LLMClient manifest's ``spec.guardrails``. On each prompt, the linked, active
    guardrails run on the user's message and the LLM's reply, in order of their priority.

    **Usage Example**

    .. code-block:: python

        LLMClientGuardrails.objects.create(llmclient=my_llmclient, guardrail=my_guardrail)
        guardrails = LLMClientGuardrails.guardrails_for(my_llmclient)
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMClient Guardrails"
        unique_together = ("llmclient", "guardrail")

    #: The LLMClient that the guardrail protects.
    llmclient = models.ForeignKey(LLMClient, on_delete=models.CASCADE)

    guardrail = models.ForeignKey(
        Guardrail,
        on_delete=models.CASCADE,
        related_name="llmclient_guardrails",
        help_text="The Guardrail.",
    )

    @classmethod
    def guardrails_for(cls, llmclient: LLMClient) -> list[Guardrail]:
        """
        Return the active Guardrails of a LLMClient, in order of priority and then id.

        :param llmclient: The LLMClient.
        :returns: The LLMClient's active guardrails.
        :rtype: list[Guardrail]
        """
        return [
            link.guardrail
            for link in cls.objects.filter(llmclient=llmclient, guardrail__is_active=True)
            .select_related("guardrail", "guardrail__user_profile__user")
            .order_by("guardrail__priority", "guardrail__id")
        ]


__all__ = [
    "LLMClientGuardrails",
]
