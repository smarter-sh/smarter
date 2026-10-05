"""
Record :class:`~smarter.apps.guardrail.models.GuardrailEvent` rows: the audit trail of guardrails.

For the ``pii`` and ``secrets`` categories, the excerpt is masked, so that the event does not
store the personal data or secret that the guardrail detected: personal data keeps its last
four characters, and secrets only their length.
"""

from typing import Any, Optional

from smarter.apps.guardrail.models import (
    Guardrail,
    GuardrailCategory,
    GuardrailEvent,
)
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailFinding,
    GuardrailStage,
)
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])

MAX_EXCERPT_LENGTH = 500
MAX_EXCERPT_MATCHES = 10


def mask(text: str, category: str) -> str:
    """
    Mask a match, for an event's excerpt.

    :param text: The matched text.
    :param category: The guardrail's category.
    :returns: For secrets, only the length; for personal data, the last four characters;
        otherwise the text.
    """
    if category == GuardrailCategory.SECRETS:
        return f"[{len(text)} characters]"
    if category == GuardrailCategory.PII:
        return "*" * max(len(text) - 4, 4) + (text[-4:] if len(text) >= 8 else "")
    return text


def excerpt(finding: GuardrailFinding, segment_text: Optional[str]) -> Optional[str]:
    """Return the excerpt of a finding, for its event: its matches, or the segment, masked for the ``pii`` and ``secrets`` categories."""
    if finding.matches:
        parts = [
            (
                f"{match.label}: {mask(match.text, finding.category)}"
                if match.label
                else mask(match.text, finding.category)
            )
            for match in finding.matches[:MAX_EXCERPT_MATCHES]
        ]
        return "; ".join(parts)[:MAX_EXCERPT_LENGTH]
    if not segment_text:
        return None
    if finding.category in (GuardrailCategory.PII, GuardrailCategory.SECRETS):
        return f"[{len(segment_text)} characters]"
    return segment_text[:MAX_EXCERPT_LENGTH]


def stage_name(stage: GuardrailStage) -> str:
    """Return the Guardrail stage of a pipeline stage: input or output."""
    return "input" if stage == GuardrailStage.PRE else "output"


def record_event(  # pylint: disable=too-many-arguments
    *,
    guardrail: Guardrail,
    stage: GuardrailStage,
    disposition: str,
    finding: Optional[GuardrailFinding] = None,
    segment_text: Optional[str] = None,
    error: Optional[str] = None,
    llmclient: Any = None,
    session_key: Optional[str] = None,
) -> Optional[GuardrailEvent]:
    """
    Record a guardrail event.

    A failure to record is logged, and does not fail the prompt.

    :returns: The event, or ``None`` if it could not be recorded.
    """
    try:
        return GuardrailEvent.objects.create(
            guardrail=guardrail if guardrail.pk else None,
            guardrail_name=guardrail.name,
            llmclient=llmclient if getattr(llmclient, "pk", None) else None,
            session_key=session_key,
            stage=stage_name(stage),
            category=guardrail.category,
            strategy=guardrail.strategy,
            action=guardrail.action,
            mode=guardrail.mode,
            disposition=disposition,
            severity=guardrail.severity,
            confidence=finding.confidence if finding else None,
            excerpt=excerpt(finding, segment_text) if finding else None,
            rationale=finding.rationale if finding else None,
            error=error,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Could not record an event of guardrail '%s': %s", guardrail.name, e, exc_info=True)
        return None


__all__ = ["excerpt", "mask", "record_event", "stage_name"]
