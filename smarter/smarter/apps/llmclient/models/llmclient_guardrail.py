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
    Represents the set of callable guardrails that are available to a LLMClient instance within the Smarter platform.

    This model is used to define and manage the specific guardrails that an llmclient can access or invoke during its operation.
    Each record in this model links an llmclient to a named guardrail, enabling fine-grained control over the llmclient's capabilities.
    The available guardrails are defined by a fixed set of choices, such as "weather", "news", "prices", and "math".

    By associating guardrails with llmclients, the platform allows for extensible and customizable llmclient behavior, supporting
    use cases where different llmclients require access to different sets of features or integrations. This model is essential
    for scenarios where llmclients need to perform actions, retrieve information, or interact with external APIs in a controlled
    and auditable manner.

    **Model Relationships**

    - Each LLMClientGuardrails entry is linked to one :class:`LLMClient` instance.
    - Each entry specifies a guardrail name from a predefined set of choices.

    **Usage Example**

    .. code-block:: python

        # Assign a guardrail to an llmclient
        LLMClientGuardrails.objects.create(llmclient=my_llmclient, name="weather")

        # List all guardrails available to an llmclient
        guardrails = LLMClientGuardrails.objects.filter(llmclient=my_llmclient)

    **Notes**

    - The set of available guardrails is controlled by the ``CHOICES`` class attribute.
    - This model is intended for internal use to manage and audit llmclient capabilities.
    - Uniqueness is not enforced, so an llmclient may have multiple entries for the same guardrail if needed.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMClient Guardrails"

    #: The LLMClient instance associated with this guardrail.
    #: Example: LLMClient(id=1, name="my-llmclient")
    llmclient = models.ForeignKey(LLMClient, on_delete=models.CASCADE)

    guardrail = models.ForeignKey(
        Guardrail,
        on_delete=models.CASCADE,
        related_name="guardrail",
        help_text="The Guardrail.",
    )


__all__ = [
    "LLMClientGuardrails",
]
