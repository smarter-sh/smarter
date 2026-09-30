"""
Base class for guardrail strategies.

Each :class:`~smarter.apps.guardrail.models.GuardrailStrategy` has exactly one concrete
subclass, registered in :mod:`smarter.apps.guardrail.services.strategies.registry`. A
strategy's job is narrow: given a text segment and the Guardrail that owns it, decide whether
it triggers, with what confidence, and, for the strategies that can, where. What happens next
(block, redact, flag and so on) is the job of :mod:`smarter.apps.guardrail.services.actions`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from smarter.apps.guardrail.manifest.models.guardrail.const import DEFAULT_THRESHOLD
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailMatch,
    GuardrailStage,
    TextSegment,
)


class StrategyContext(BaseModel):
    """
    Ambient information a strategy may need beyond the text itself.

    :ivar stage: Which side of the model call is being evaluated.
    :ivar request_uid: A caller-supplied identifier for correlating strategy calls with a request.
    """

    model_config = {"arbitrary_types_allowed": True}

    stage: GuardrailStage
    request_uid: str | None = None


class StrategyMatch(BaseModel):
    """
    What a strategy hands back for a single segment.

    :ivar triggered: Whether the segment matched the guardrail.
    :ivar confidence: A confidence score in ``[0.0, 1.0]``. The deterministic strategies report
        ``1.0`` when they trigger.
    :ivar matches: Where the segment matched, for the strategies that locate what they match.
    :ivar rationale: A human-readable explanation, for events and logs.
    """

    triggered: bool
    confidence: float | None = None
    matches: list[GuardrailMatch] = Field(default_factory=list)
    rationale: str | None = None


class BaseGuardrailStrategy(ABC):
    """
    Abstract base for all guardrail strategies.

    Instances are stateless and safe to reuse across requests.
    """

    @abstractmethod
    def evaluate(self, *, segment: TextSegment, guardrail: Guardrail, context: StrategyContext) -> StrategyMatch:
        """
        Evaluate a single text segment against a single Guardrail.

        :param segment: The text segment.
        :param guardrail: The Guardrail, which supplies the strategy's configuration.
        :param context: Ambient evaluation context.
        :returns: Whether the segment triggered the guardrail, and how.
        :raises GuardrailConfigError: If the Guardrail's configuration is invalid for the
            strategy. A misconfigured guardrail must fail loudly, rather than silently pass.
        :raises GuardrailProviderError: If a call to an LLM provider fails.
        """
        raise NotImplementedError

    @staticmethod
    def threshold(guardrail: Guardrail) -> float:
        """Return the Guardrail's confidence threshold, or the default."""
        return DEFAULT_THRESHOLD if guardrail.threshold is None else guardrail.threshold


__all__ = ["BaseGuardrailStrategy", "StrategyContext", "StrategyMatch"]
