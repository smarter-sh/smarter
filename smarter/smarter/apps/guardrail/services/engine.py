"""
Evaluate one guardrail against a payload.

:class:`GuardrailEngine` runs a guardrail's strategy on each text segment of a payload, and
returns a :class:`~smarter.apps.provider.services.text_completion.contracts.GuardrailOutcome`
with a finding for each segment that triggered. It knows nothing of actions or events:
:class:`~smarter.apps.guardrail.services.pipeline.GuardrailPipeline` runs the engine and the
actions, one guardrail at a time, so that each guardrail sees the payload as changed by the
guardrails before it.
"""

import time
from typing import Any

from smarter.apps.guardrail.models import Guardrail
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailFinding,
    GuardrailOutcome,
    GuardrailStage,
)
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .exceptions import GuardrailServiceError
from .strategies.base import StrategyContext
from .strategies.registry import get_strategy
from .text_extraction import extract_segments

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])


class GuardrailEngine:
    """Evaluate guardrails against payloads.

    Stateless.
    """

    def evaluate(
        self,
        guardrail: Guardrail,
        payload: dict[str, Any],
        stage: GuardrailStage,
        context: StrategyContext,
    ) -> GuardrailOutcome:
        """
        Evaluate one guardrail against every text segment of the payload.

        Any exception raised by the strategy is recorded in the outcome's ``error``, rather
        than raised, so that one failing guardrail cannot take down the prompt.

        :param guardrail: The guardrail.
        :param payload: The chat completion request (pre stage) or response (post stage).
        :param stage: Which side of the model call the payload is.
        :param context: Ambient evaluation context.
        :returns: The outcome, with a finding for each segment that triggered.
        """
        start = time.monotonic()
        findings: list[GuardrailFinding] = []
        error: str | None = None
        try:
            strategy = get_strategy(guardrail.strategy)
            for segment in extract_segments(payload, stage):
                match = strategy.evaluate(segment=segment, guardrail=guardrail, context=context)
                if not match.triggered:
                    continue
                findings.append(
                    GuardrailFinding(
                        guardrail_id=guardrail.pk,
                        guardrail_name=guardrail.name,
                        category=guardrail.category,
                        strategy=guardrail.strategy,
                        action=guardrail.action,
                        severity=guardrail.severity,
                        triggered=True,
                        confidence=match.confidence,
                        matches=match.matches,
                        segment_path=segment.path,
                        rationale=match.rationale,
                    )
                )
        except GuardrailServiceError as e:
            error = str(e)
            logger.error("Guardrail '%s' failed to evaluate: %s", guardrail.name, error)
        except Exception as e:  # pylint: disable=broad-exception-caught
            error = f"Unexpected error: {type(e).__name__}: {e}"
            logger.error("Guardrail '%s' raised an unexpected error: %s", guardrail.name, error, exc_info=True)
        return GuardrailOutcome(
            guardrail_id=guardrail.pk,
            guardrail_name=guardrail.name,
            mode=guardrail.mode,
            fail_closed=guardrail.fail_closed,
            priority=guardrail.priority,
            findings=findings,
            error=error,
            duration_ms=(time.monotonic() - start) * 1000,
        )


__all__ = ["GuardrailEngine"]
