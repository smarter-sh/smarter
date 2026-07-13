"""Base class for guardrail match strategies.

Each :class:`smarter.apps.guardrail.models.MatchStrategy` choice gets
exactly one concrete subclass, registered in
:mod:`smarter.apps.guardrail.services.strategies.registry`. A
strategy's job is narrow: given a text segment and the
:class:`~smarter.apps.guardrail.models.Guardrail` row that owns it,
decide whether it triggers and with what confidence. Everything about
*what happens next* (block/redact/flag/etc.) is the action layer's job
(:mod:`smarter.apps.guardrail.services.actions`), not the strategy's —
this keeps strategies swappable and testable in isolation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.services.contracts import GuardrailStage, TextSegment


class StrategyContext(BaseModel):
    """Ambient information a strategy may need beyond the text itself.

    :ivar stage: Which side of the model call is being evaluated.
    :vartype stage: ~smarter.apps.guardrail.services.contracts.GuardrailStage
    :ivar account_id: The evaluating :class:`~smarter.apps.account.models.Account`'s
        primary key.
    :vartype account_id: int or None
    :ivar user_profile_id: The evaluating :class:`~smarter.apps.account.models.UserProfile`'s
        primary key, if scoped to one.
    :vartype user_profile_id: int or None
    :ivar request_uid: A caller-supplied identifier for correlating
        strategy calls with a specific request.
    :vartype request_uid: str or None
    """

    model_config = {"arbitrary_types_allowed": True}

    stage: GuardrailStage
    user_profile_id: int | None = None
    request_uid: str | None = None


class StrategyMatch(BaseModel):
    """What a strategy hands back for a single segment evaluation.

    :ivar triggered: Whether the segment matched the guardrail.
    :vartype triggered: bool
    :ivar confidence: A confidence score in ``[0.0, 1.0]``, for scored
        strategies (``semantic``, ``model``, ``llm_judge``). Binary
        strategies (``regex``, ``keyword``) report ``1.0`` when
        triggered.
    :vartype confidence: float or None
    :ivar matched_text: The specific text that triggered the match, when
        available.
    :vartype matched_text: str or None
    :ivar rationale: A human-readable explanation of the match, for
        logging and findings.
    :vartype rationale: str or None
    """

    triggered: bool
    confidence: float | None = None
    matched_text: str | None = None
    rationale: str | None = None


class BaseGuardrailStrategy(ABC):
    """Abstract base for all guardrail match strategies.

    Subclass and implement :meth:`evaluate`. Instances are stateless and
    safe to cache/reuse across requests — do not store per-request state
    on ``self``.
    """

    @abstractmethod
    def evaluate(
        self,
        *,
        segment: TextSegment,
        guardrail: Guardrail,
        context: StrategyContext,
    ) -> StrategyMatch:
        """Evaluate a single text segment against a single Guardrail row.

        :param segment: The text segment to evaluate.
        :type segment: ~smarter.apps.guardrail.services.contracts.TextSegment
        :param guardrail: The guardrail row supplying the strategy's
            configuration (``pattern``, ``config``,
            ``confidence_threshold``).
        :type guardrail: ~smarter.apps.guardrail.models.Guardrail
        :param context: Ambient evaluation context.
        :type context: StrategyContext
        :returns: Whether ``segment`` triggered ``guardrail``, and with
            what confidence/rationale.
        :rtype: StrategyMatch
        :raises smarter.apps.guardrail.services.exceptions.GuardrailConfigError:
            If ``guardrail.pattern``/``guardrail.config`` is malformed
            or incomplete for this strategy. Implementations should
            raise rather than silently return ``triggered=False`` — a
            misconfigured guardrail failing open is worse than it
            failing loud at evaluation time.
        """
        raise NotImplementedError

    def meets_threshold(self, guardrail: Guardrail, confidence: float | None) -> bool:
        """Check whether a confidence score clears the guardrail's threshold.

        Binary (non-scored) strategies (``regex``, ``keyword``) don't
        need this — it exists for the scored strategies (``semantic``,
        ``model``, ``llm_judge``).

        :param guardrail: The guardrail supplying
            ``confidence_threshold``.
        :type guardrail: ~smarter.apps.guardrail.models.Guardrail
        :param confidence: The confidence score to check, or ``None``.
        :type confidence: float or None
        :returns: ``True`` if ``guardrail.confidence_threshold`` or
            ``confidence`` is unset (nothing to gate on), or if
            ``confidence`` meets or exceeds the threshold.
        :rtype: bool
        """
        if guardrail.confidence_threshold is None or confidence is None:
            return True
        return confidence >= guardrail.confidence_threshold


__all__ = ["BaseGuardrailStrategy", "StrategyContext", "StrategyMatch"]
