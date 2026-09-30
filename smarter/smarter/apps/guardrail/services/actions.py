"""
Apply a triggered guardrail's action to the payload.

Each action returns an :class:`ActionOutcome`: the payload, possibly changed; the pipeline
disposition; the disposition to record in the :class:`~smarter.apps.guardrail.models.GuardrailEvent`;
and, for ``block``, the user-facing message.

A guardrail in ``monitor`` mode never changes the payload nor the disposition. Its event
records ``monitored``, i.e. what it would have done.
"""

from dataclasses import dataclass
from typing import Any

from smarter.apps.guardrail.models import (
    Guardrail,
    GuardrailAction,
    GuardrailDisposition,
    GuardrailMode,
    GuardrailStrategy,
)
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailFinding,
    GuardrailMatch,
    PipelineDisposition,
)
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .strategies.regex_strategy import compiled_pattern
from .text_extraction import read_segment, write_segment

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])

LABEL_PLACEHOLDER = "{label}"
"""A placeholder in ``replacement`` that redact replaces with what was matched, e.g. credit_card."""


@dataclass
class ActionOutcome:
    """
    The result of applying one guardrail's action to one finding.

    :ivar payload: The payload, changed by redact and transform.
    :ivar disposition: The pipeline disposition this action resolves to.
    :ivar event_disposition: What to record in the guardrail's event.
    :ivar message: The user-facing message, for block.
    :ivar halt_pipeline: True for block: no further guardrails run.
    """

    payload: dict[str, Any]
    disposition: PipelineDisposition
    event_disposition: str
    message: str | None = None
    halt_pipeline: bool = False


def replace_matches(text: str, matches: list[GuardrailMatch], replacement: str) -> str:
    """
    Replace each match in text, from the last to the first, so that the positions of the.

    earlier matches remain valid. ``{label}`` in the replacement is the match's label.
    """
    for match in sorted(matches, key=lambda m: m.start, reverse=True):
        value = replacement.replace(LABEL_PLACEHOLDER, match.label or "")
        text = text[: match.start] + value + text[match.end :]
    return text


def apply_action(*, payload: dict[str, Any], finding: GuardrailFinding, guardrail: Guardrail) -> ActionOutcome:
    """
    Apply the guardrail's action to the payload, for a triggered finding.

    :param payload: The payload, as changed by the guardrails that ran before this one.
    :param finding: The triggered finding.
    :param guardrail: The guardrail.
    :returns: The outcome.
    """
    if guardrail.mode == GuardrailMode.MONITOR:
        logger.info(
            "Guardrail '%s' triggered in monitor mode; action %s was not taken: %s",
            guardrail.name,
            guardrail.action,
            finding.rationale,
        )
        return ActionOutcome(payload, PipelineDisposition.ALLOWED, GuardrailDisposition.MONITORED)
    handler = _ACTION_HANDLERS.get(guardrail.action, _handle_flag)
    return handler(payload=payload, finding=finding, guardrail=guardrail)


# pylint: disable=W0613
def _handle_log(*, payload, finding, guardrail) -> ActionOutcome:
    """``log``: record the event only."""
    return ActionOutcome(payload, PipelineDisposition.ALLOWED, GuardrailDisposition.LOGGED)


def _handle_flag(*, payload, finding, guardrail) -> ActionOutcome:
    """``flag``: record the event for review, and continue."""
    return ActionOutcome(payload, PipelineDisposition.FLAGGED, GuardrailDisposition.FLAGGED)


def _handle_escalate(*, payload, finding, guardrail) -> ActionOutcome:
    """``escalate``: record the event for human review, and continue.

    The pipeline sends ``guardrail_escalated``.
    """
    return ActionOutcome(payload, PipelineDisposition.ESCALATED, GuardrailDisposition.ESCALATED)


def _handle_block(*, payload, finding, guardrail) -> ActionOutcome:
    """``block``: stop, and return the guardrail's message."""
    return ActionOutcome(
        payload,
        PipelineDisposition.BLOCKED,
        GuardrailDisposition.BLOCKED,
        message=guardrail.effective_message,
        halt_pipeline=True,
    )


def _handle_redact(*, payload, finding, guardrail) -> ActionOutcome:
    """``redact``: replace every match with the guardrail's replacement."""
    text = read_segment(payload, finding.segment_path or "")
    if text is None or not finding.matches:
        logger.warning("Guardrail '%s' could not redact %s; flagging instead.", guardrail.name, finding.segment_path)
        return _handle_flag(payload=payload, finding=finding, guardrail=guardrail)
    redacted = replace_matches(text, finding.matches, guardrail.effective_replacement)
    return ActionOutcome(
        write_segment(payload, finding.segment_path, redacted),  # type: ignore[arg-type]
        PipelineDisposition.REDACTED,
        GuardrailDisposition.REDACTED,
    )


def _handle_transform(*, payload, finding, guardrail) -> ActionOutcome:
    """
    ``transform``: replace every match with the guardrail's replacement.

    For the regex strategy, the replacement is a regex replacement template, which may refer
    to the pattern's groups, e.g. ``\\1``.
    """
    text = read_segment(payload, finding.segment_path or "")
    if text is None or not finding.matches or guardrail.replacement is None:
        logger.warning("Guardrail '%s' could not transform %s; flagging instead.", guardrail.name, finding.segment_path)
        return _handle_flag(payload=payload, finding=finding, guardrail=guardrail)
    if guardrail.strategy == GuardrailStrategy.REGEX:
        transformed = compiled_pattern(guardrail).sub(guardrail.replacement, text)
    else:
        transformed = replace_matches(text, finding.matches, guardrail.replacement)
    return ActionOutcome(
        write_segment(payload, finding.segment_path, transformed),  # type: ignore[arg-type]
        PipelineDisposition.TRANSFORMED,
        GuardrailDisposition.TRANSFORMED,
    )


_ACTION_HANDLERS = {
    GuardrailAction.LOG: _handle_log,
    GuardrailAction.FLAG: _handle_flag,
    GuardrailAction.REDACT: _handle_redact,
    GuardrailAction.TRANSFORM: _handle_transform,
    GuardrailAction.BLOCK: _handle_block,
    GuardrailAction.ESCALATE: _handle_escalate,
}


__all__ = ["ActionOutcome", "apply_action", "replace_matches"]
