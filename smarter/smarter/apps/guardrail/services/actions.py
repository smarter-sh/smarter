"""Apply a triggered guardrail's action to a payload.

Strategies (see :mod:`smarter.apps.guardrail.services.strategies`)
decide *whether* something matched; this module decides *what happens
to the payload* as a result. Every handler has the signature
``(payload, finding, guardrail) -> ActionOutcome`` and is pure — it
returns a new payload rather than mutating in place, so the pipeline
can compose handlers across multiple triggered guardrails without
cross-talk.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from smarter.apps.guardrail.models import GuardrailAction
from smarter.apps.guardrail.services.contracts import (
    GuardrailFinding,
    PipelineDisposition,
)
from smarter.apps.guardrail.services.text_extraction import resolve_path, write_segment
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

if TYPE_CHECKING:
    from smarter.apps.guardrail.models import Guardrail

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])


@dataclass
class ActionOutcome:
    """The result of applying one guardrail's action to a payload.

    :ivar payload: The payload after the action has been applied. Equal
        to the input payload for actions that don't mutate it
        (``ALLOW``, ``FLAG``, ``ESCALATE``, and ``BLOCK``, whose
        semantics is to withhold the payload rather than alter it).
    :vartype payload: dict[str, typing.Any]
    :ivar disposition: The :class:`~smarter.apps.guardrail.services.contracts.PipelineDisposition`
        this action resolved to.
    :vartype disposition: ~smarter.apps.guardrail.services.contracts.PipelineDisposition
    :ivar fallback_message: The user-facing message to show, set only
        when ``disposition`` is ``BLOCKED``.
    :vartype fallback_message: str or None
    :ivar halt_pipeline: Whether the pipeline should stop evaluating any
        remaining, lower-priority guardrails' actions. ``True`` only for
        ``BLOCK`` — there is no point running further guardrails once
        the request is dead.
    :vartype halt_pipeline: bool
    """

    payload: dict[str, Any]
    disposition: PipelineDisposition
    fallback_message: str | None = None
    halt_pipeline: bool = False


_REDACTION_TOKEN = "[REDACTED]"


def apply_action(
    *,
    payload: dict[str, Any],
    finding: GuardrailFinding,
    guardrail: Guardrail,
) -> ActionOutcome:
    """Apply ``guardrail.action`` to ``payload`` for a triggered ``finding``.

    If ``guardrail.is_blocking`` is ``False``, every action is forced
    into shadow mode: the finding is logged as if it triggered, but the
    payload and disposition are left untouched (``ALLOWED``) regardless
    of the configured action.

    :param payload: The current payload, as mutated by any
        higher-priority guardrails evaluated earlier in the same
        pipeline run.
    :type payload: dict[str, typing.Any]
    :param finding: The triggered finding to act on.
    :type finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :param guardrail: The ORM row that produced ``finding``, supplying
        ``action``, ``is_blocking``, ``config``, and ``fallback_message``.
    :type guardrail: ~smarter.apps.guardrail.models.Guardrail
    :returns: The outcome of applying the guardrail's action.
    :rtype: ActionOutcome
    """
    if not guardrail.is_blocking:
        logger.info(
            "Guardrail '%s' triggered in shadow mode (action=%s suppressed): %s",
            guardrail.name,
            guardrail.action,
            finding.rationale,
        )
        return ActionOutcome(payload=payload, disposition=PipelineDisposition.ALLOWED)

    handler = _ACTION_HANDLERS.get(guardrail.action)
    if handler is None:
        logger.warning("No action handler registered for action='%s'; defaulting to FLAG.", guardrail.action)
        handler = _handle_flag
    return handler(payload=payload, finding=finding, guardrail=guardrail)


def _handle_allow(*, payload, finding, guardrail) -> ActionOutcome:
    """Handle ``GuardrailAction.ALLOW`` — log only, payload unchanged.

    :param payload: The current payload.
    :type payload: dict[str, typing.Any]
    :param finding: The triggered finding.
    :type finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :param guardrail: The originating guardrail row.
    :type guardrail: ~smarter.apps.guardrail.models.Guardrail
    :returns: An outcome with ``disposition=ALLOWED`` and the payload
        unchanged.
    :rtype: ActionOutcome
    """
    logger.debug("Guardrail '%s' triggered with action=ALLOW (log only).", guardrail.name)
    return ActionOutcome(payload=payload, disposition=PipelineDisposition.ALLOWED)


def _handle_flag(*, payload, finding, guardrail) -> ActionOutcome:
    """Handle ``GuardrailAction.FLAG`` — mark for review, payload unchanged.

    :param payload: The current payload.
    :type payload: dict[str, typing.Any]
    :param finding: The triggered finding.
    :type finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :param guardrail: The originating guardrail row.
    :type guardrail: ~smarter.apps.guardrail.models.Guardrail
    :returns: An outcome with ``disposition=FLAGGED`` and the payload
        unchanged.
    :rtype: ActionOutcome
    """
    logger.info("Guardrail '%s' flagged content for review: %s", guardrail.name, finding.rationale)
    return ActionOutcome(payload=payload, disposition=PipelineDisposition.FLAGGED)


def _handle_redact(*, payload, finding, guardrail) -> ActionOutcome:
    """Handle ``GuardrailAction.REDACT`` — replace matched text in place.

    :param payload: The current payload.
    :type payload: dict[str, typing.Any]
    :param finding: The triggered finding; requires ``segment_path`` and
        ``matched_text`` to be set.
    :type finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :param guardrail: The originating guardrail row.
    :type guardrail: ~smarter.apps.guardrail.models.Guardrail
    :returns: An outcome with ``disposition=REDACTED`` and the matched
        text replaced by a redaction token, or ``disposition=FLAGGED``
        with the payload unchanged if the finding lacks the fields
        needed to locate the match.
    :rtype: ActionOutcome
    """
    if not finding.segment_path or not finding.matched_text:
        logger.warning(
            "Guardrail '%s' action=REDACT but finding has no segment_path/matched_text; leaving payload unchanged.",
            guardrail.name,
        )
        return ActionOutcome(payload=payload, disposition=PipelineDisposition.FLAGGED)

    updated = _redact_in_place(payload, finding)
    logger.info("Guardrail '%s' redacted matched text at %s.", guardrail.name, finding.segment_path)
    return ActionOutcome(payload=updated, disposition=PipelineDisposition.REDACTED)


def _redact_in_place(payload: dict[str, Any], finding: GuardrailFinding) -> dict[str, Any]:
    """Replace ``finding.matched_text`` with a redaction token.

    :param payload: The payload to redact.
    :type payload: dict[str, typing.Any]
    :param finding: The finding supplying ``segment_path`` and
        ``matched_text``.
    :type finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :returns: A copy of ``payload`` with the match replaced, or
        ``payload`` unchanged if ``segment_path`` does not resolve to a
        string field.
    :rtype: dict[str, typing.Any]
    """
    node, key = resolve_path(payload, finding.segment_path)
    if node is None:
        return payload
    original = node.get(key) if isinstance(node, dict) else None
    if not isinstance(original, str):
        return payload
    redacted_text = original.replace(finding.matched_text, _REDACTION_TOKEN)
    return write_segment(payload, finding.segment_path, redacted_text)


def _handle_transform(*, payload, finding, guardrail) -> ActionOutcome:
    """Handle ``GuardrailAction.TRANSFORM`` — substitute matched text.

    Expects ``guardrail.config["replacement"]``, a literal string
    substituted for the matched text. More elaborate rewriting (e.g.
    routing through an LLM to rephrase) belongs in a dedicated
    strategy/action pair layered on top of this one; this handler
    covers the common literal-substitution case out of the box.

    :param payload: The current payload.
    :type payload: dict[str, typing.Any]
    :param finding: The triggered finding; requires ``segment_path`` and
        ``matched_text`` to be set.
    :type finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :param guardrail: The originating guardrail row; requires
        ``config["replacement"]`` to be set.
    :type guardrail: ~smarter.apps.guardrail.models.Guardrail
    :returns: An outcome with ``disposition=TRANSFORMED`` and the
        matched text replaced, or ``disposition=FLAGGED`` with the
        payload unchanged if the replacement or finding details are
        missing.
    :rtype: ActionOutcome
    """
    replacement = guardrail.config.get("replacement")
    if replacement is None or not finding.segment_path or not finding.matched_text:
        logger.warning(
            "Guardrail '%s' action=TRANSFORM but config.replacement or finding details are missing; "
            "falling back to FLAG.",
            guardrail.name,
        )
        return ActionOutcome(payload=payload, disposition=PipelineDisposition.FLAGGED)

    node, key = resolve_path(payload, finding.segment_path)
    if node is None:
        return ActionOutcome(payload=payload, disposition=PipelineDisposition.FLAGGED)
    original = node.get(key) if isinstance(node, dict) else None
    if not isinstance(original, str):
        return ActionOutcome(payload=payload, disposition=PipelineDisposition.FLAGGED)

    transformed_text = original.replace(finding.matched_text, replacement)
    updated = write_segment(payload, finding.segment_path, transformed_text)
    logger.info("Guardrail '%s' transformed matched text at %s.", guardrail.name, finding.segment_path)
    return ActionOutcome(payload=updated, disposition=PipelineDisposition.TRANSFORMED)


def _handle_block(*, payload, finding, guardrail) -> ActionOutcome:
    """Handle ``GuardrailAction.BLOCK`` — withhold the request/response.

    :param payload: The current payload; returned unchanged, since a
        blocked request is discarded by the caller rather than used.
    :type payload: dict[str, typing.Any]
    :param finding: The triggered finding.
    :type finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :param guardrail: The originating guardrail row; supplies
        ``fallback_message``.
    :type guardrail: ~smarter.apps.guardrail.models.Guardrail
    :returns: An outcome with ``disposition=BLOCKED``,
        ``halt_pipeline=True``, and ``fallback_message`` set from
        ``guardrail.fallback_message`` (or a generic default).
    :rtype: ActionOutcome
    """
    message = guardrail.fallback_message or "This request was blocked by a content guardrail."
    logger.warning("Guardrail '%s' blocked the request: %s", guardrail.name, finding.rationale)
    return ActionOutcome(
        payload=payload,
        disposition=PipelineDisposition.BLOCKED,
        fallback_message=message,
        halt_pipeline=True,
    )


def _handle_escalate(*, payload, finding, guardrail) -> ActionOutcome:
    """Handle ``GuardrailAction.ESCALATE`` — route to human review.

    .. todo::
        Wire this to whatever human-review queue or notification
        channel the platform uses (e.g. an ``EscalationTicket``
        resource or a Slack webhook). Left as a clear extension point
        rather than a silent no-op.

    :param payload: The current payload; returned unchanged.
    :type payload: dict[str, typing.Any]
    :param finding: The triggered finding.
    :type finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :param guardrail: The originating guardrail row.
    :type guardrail: ~smarter.apps.guardrail.models.Guardrail
    :returns: An outcome with ``disposition=ESCALATED`` and the payload
        unchanged.
    :rtype: ActionOutcome
    """
    logger.warning(
        "Guardrail '%s' escalated to human review (severity=%d): %s",
        guardrail.name,
        guardrail.severity,
        finding.rationale,
    )
    return ActionOutcome(payload=payload, disposition=PipelineDisposition.ESCALATED)


_ACTION_HANDLERS = {
    GuardrailAction.ALLOW: _handle_allow,
    GuardrailAction.FLAG: _handle_flag,
    GuardrailAction.REDACT: _handle_redact,
    GuardrailAction.TRANSFORM: _handle_transform,
    GuardrailAction.BLOCK: _handle_block,
    GuardrailAction.ESCALATE: _handle_escalate,
}

__all__ = ["apply_action", "ActionOutcome"]
