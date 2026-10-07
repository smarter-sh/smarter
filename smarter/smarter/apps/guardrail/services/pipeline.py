"""
The entry point of the guardrail service for the prompt pipeline.

:class:`GuardrailPipeline` runs an LLMClient's guardrails on the user's message before it is
sent to the LLM (:meth:`~GuardrailPipeline.run_pre`), and on the LLM's reply before it is
returned to the user (:meth:`~GuardrailPipeline.run_post`), and folds their outcomes into a
single :class:`~smarter.apps.provider.services.text_completion.contracts.PipelineResult`.

.. code-block:: python

    pipeline = GuardrailPipeline.for_llmclient(llmclient, session_key=session_key)
    pre = pipeline.run_pre({"messages": messages})
    if pre.blocked:
        return pre.message
    messages = pre.payload["messages"]  # possibly redacted
    response = call_llm(messages)
    post = pipeline.run_post(response)
    reply = post.message if post.blocked else post.payload

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import time
from typing import Any, Iterable, Optional

from smarter.apps.guardrail.models import (
    Guardrail,
    GuardrailDisposition,
    GuardrailMode,
)
from smarter.apps.guardrail.signals import (
    guardrail_blocked,
    guardrail_escalated,
    guardrail_failed,
    guardrail_triggered,
)
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailOutcome,
    GuardrailStage,
    PipelineDisposition,
    PipelineResult,
)
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .actions import apply_action
from .engine import GuardrailEngine
from .events import record_event, stage_name
from .strategies.base import StrategyContext
from .text_extraction import read_segment

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])

# The precedence with which the dispositions of several guardrails fold into one. Higher wins.
_DISPOSITION_PRECEDENCE = [
    PipelineDisposition.ALLOWED,
    PipelineDisposition.FLAGGED,
    PipelineDisposition.REDACTED,
    PipelineDisposition.TRANSFORMED,
    PipelineDisposition.ESCALATED,
    PipelineDisposition.BLOCKED,
]


def fold(current: PipelineDisposition, incoming: PipelineDisposition) -> PipelineDisposition:
    """Return whichever of two dispositions ranks higher."""
    if _DISPOSITION_PRECEDENCE.index(incoming) > _DISPOSITION_PRECEDENCE.index(current):
        return incoming
    return current


class GuardrailPipeline:
    """
    Run a set of guardrails on a prompt's input and output.

    The guardrails run one at a time, in order of ``priority`` then id, each on the payload as
    changed by the guardrails before it: e.g. an LLM judge that runs after a PII redaction
    guardrail sees the redacted text. The first guardrail that blocks stops the pipeline, so
    that no further, possibly costly, guardrails run.

    A guardrail that fails to run, e.g. because its LLM provider is unavailable, is recorded,
    and skipped, unless it is ``failClosed``, in which case it blocks.

    Every triggered guardrail, and every failure, is recorded as a
    :class:`~smarter.apps.guardrail.models.GuardrailEvent`, unless ``record_events`` is false.

    :param guardrails: The guardrails. Inactive guardrails, and those of the other stage, are skipped.
    :param llmclient: The LLMClient of the prompt, for the events.
    :param session_key: The session key of the prompt, for the events.
    :param record_events: Whether to record events. False for dry runs.
    """

    def __init__(
        self,
        guardrails: Iterable[Guardrail],
        *,
        llmclient: Any = None,
        session_key: Optional[str] = None,
        record_events: bool = True,
    ):
        self.guardrails = sorted((g for g in guardrails if g.is_active), key=lambda g: (g.priority, g.pk or 0))
        self.llmclient = llmclient
        self.session_key = session_key
        self.record_events = record_events
        self._engine = GuardrailEngine()

    @classmethod
    def for_llmclient(cls, llmclient: Any, session_key: Optional[str] = None) -> "GuardrailPipeline":
        """Return a pipeline for the guardrails of an LLMClient, as listed in its manifest's ``spec.guardrails``."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmclient.models import LLMClientGuardrails

        return cls(LLMClientGuardrails.guardrails_for(llmclient), llmclient=llmclient, session_key=session_key)

    def guardrails_for(self, stage: GuardrailStage) -> list[Guardrail]:
        """Return the pipeline's guardrails that run on a stage."""
        return [g for g in self.guardrails if g.runs_on(stage_name(stage))]

    def run_pre(self, request_json: dict[str, Any], *, request_uid: Optional[str] = None) -> PipelineResult:
        """
        Run the input guardrails on the latest user message of a chat completion request.

        :param request_json: The request, with its ``messages``.
        :returns: The result. Use its ``payload``, which may be redacted, as the request.
        """
        return self._run(payload=request_json, stage=GuardrailStage.PRE, request_uid=request_uid)

    def run_post(self, response_json: dict[str, Any], *, request_uid: Optional[str] = None) -> PipelineResult:
        """
        Run the output guardrails on the reply of a chat completion response.

        :param response_json: The response, with its ``choices``.
        :returns: The result. Use its ``payload``, which may be redacted, as the response.
        """
        return self._run(payload=response_json, stage=GuardrailStage.POST, request_uid=request_uid)

    def _record(self, **kwargs):
        """Record an event, unless this is a dry run."""
        if not self.record_events:
            return None
        return record_event(llmclient=self.llmclient, session_key=self.session_key, **kwargs)

    # pylint: disable=too-many-locals
    def _run(self, *, payload: dict[str, Any], stage: GuardrailStage, request_uid: Optional[str]) -> PipelineResult:
        start = time.monotonic()
        context = StrategyContext(stage=stage, request_uid=request_uid)
        stage_value = stage_name(stage)
        working = payload
        disposition = PipelineDisposition.ALLOWED
        message: Optional[str] = None
        outcomes: list[GuardrailOutcome] = []
        halted = False

        for guardrail in self.guardrails_for(stage):
            outcome = self._engine.evaluate(guardrail, working, stage, context)
            outcomes.append(outcome)

            if outcome.error:
                blocks = guardrail.fail_closed and guardrail.mode == GuardrailMode.ENFORCE
                self._record(
                    guardrail=guardrail,
                    stage=stage,
                    disposition=GuardrailDisposition.BLOCKED if blocks else GuardrailDisposition.ERROR,
                    error=outcome.error,
                )
                guardrail_failed.send(
                    sender=self.__class__,
                    guardrail=guardrail,
                    stage=stage_value,
                    error=outcome.error,
                    fail_closed=blocks,
                )
                if blocks:
                    disposition, message, halted = PipelineDisposition.BLOCKED, guardrail.effective_message, True
                    break
                continue

            for finding in outcome.findings:
                segment_text = read_segment(working, finding.segment_path or "")
                action = apply_action(payload=working, finding=finding, guardrail=guardrail)
                working = action.payload
                disposition = fold(disposition, action.disposition)
                event = self._record(
                    guardrail=guardrail,
                    stage=stage,
                    disposition=action.event_disposition,
                    finding=finding,
                    segment_text=segment_text,
                )
                guardrail_triggered.send(
                    sender=self.__class__,
                    guardrail=guardrail,
                    stage=stage_value,
                    disposition=action.event_disposition,
                    event=event,
                )
                if action.event_disposition == GuardrailDisposition.ESCALATED:
                    guardrail_escalated.send(sender=self.__class__, guardrail=guardrail, stage=stage_value, event=event)
                if action.halt_pipeline:
                    message, halted = action.message, True
                    guardrail_blocked.send(
                        sender=self.__class__, guardrail=guardrail, stage=stage_value, message=message, event=event
                    )
                    break
            if halted:
                break

        result = PipelineResult(
            stage=stage,
            disposition=disposition,
            payload=working,
            fallback_message=message,
            outcomes=outcomes,
            guardrails_evaluated=len(outcomes),
            total_duration_ms=(time.monotonic() - start) * 1000,
            request_uid=request_uid,
        )
        logger.info(
            "GuardrailPipeline[%s] ran %d guardrail(s) in %.1fms: %s",
            stage.value,
            len(outcomes),
            result.total_duration_ms,
            disposition.value,
        )
        return result


__all__ = ["GuardrailPipeline", "fold"]
