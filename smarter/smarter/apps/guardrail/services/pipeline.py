"""The Harness-facing entry point for the guardrail pipeline.

:class:`~smarter.apps.guardrail.services.pipeline.GuardrailPipeline`
wraps :class:`~smarter.apps.guardrail.services.engine.GuardrailEngine`
(evaluation) and
:func:`~smarter.apps.guardrail.services.actions.apply_action` (payload
mutation/blocking) into two methods matching the two moments the
Harness needs a verdict: :meth:`~GuardrailPipeline.run_pre`, before
calling the LLM provider, and :meth:`~GuardrailPipeline.run_post`,
after calling it.

:Example:

.. code-block:: python

    pipeline = GuardrailPipeline(account=harness.account, user_profile=harness.user_profile)

    pre_result = pipeline.run_pre(pre_json, request_uid=request_uid)
    if pre_result.blocked:
        return error_response(pre_result.fallback_message)
    pre_json = pre_result.payload  # possibly redacted/transformed

    response_json = call_llm_provider(pre_json)

    post_result = pipeline.run_post(pre_json, response_json, request_uid=request_uid)
    if post_result.blocked:
        return error_response(post_result.fallback_message)
    response_json = post_result.payload

An arbitrary number of Guardrail rows can be attached to an
account/user_profile — the pipeline doesn't care how many; it always
runs the full active, ordered set for the stage in question and folds
their outcomes into a single verdict.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.services.actions import ActionOutcome, apply_action
from smarter.apps.guardrail.services.contracts import (
    GuardrailStage,
    PipelineDisposition,
    PipelineResult,
)
from smarter.apps.guardrail.services.engine import GuardrailEngine
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])

# Precedence used when folding multiple non-blocking triggered findings
# into one overall disposition. Higher index wins.
_DISPOSITION_PRECEDENCE = [
    PipelineDisposition.ALLOWED,
    PipelineDisposition.FLAGGED,
    PipelineDisposition.REDACTED,
    PipelineDisposition.TRANSFORMED,
    PipelineDisposition.ESCALATED,
    PipelineDisposition.BLOCKED,
]


class GuardrailPipeline:
    """Evaluate an account's Guardrail rules against a chat-completion.

    request and/or response, and fold the results into a single verdict.

    ``GuardrailPipeline`` is the sole integration point between the
    Harness and the guardrail subsystem. It is constructed once per
    account/user_profile scope and exposes exactly two public methods,
    :meth:`run_pre` and :meth:`run_post`, corresponding to the two
    moments the Harness needs a verdict: immediately before a request is
    sent to the LLM provider, and immediately after a response comes
    back.

    Internally, each call delegates evaluation to a
    :class:`~smarter.apps.guardrail.services.engine.GuardrailEngine`,
    which loads every active
    :class:`~smarter.apps.guardrail.models.Guardrail` row applicable to
    the stage (``guardrail_type`` of ``INPUT``/``OUTPUT``/``BOTH``),
    orders them by ``priority`` (lower runs first), and runs each row's
    configured :class:`~smarter.apps.guardrail.models.MatchStrategy`
    against every scannable text segment of the payload. Triggered
    findings are then passed to
    :func:`~smarter.apps.guardrail.services.actions.apply_action`, which
    applies the row's configured
    :class:`~smarter.apps.guardrail.models.GuardrailAction`
    (``ALLOW``/``FLAG``/``REDACT``/``TRANSFORM``/``BLOCK``/``ESCALATE``)
    against the payload.

    There is no limit on the number of Guardrail rows evaluated per
    call — an account may attach an arbitrary, indefinite number of
    guardrails, and every active one applicable to the stage is run.
    Rows are evaluated in full (a failure or trigger on one guardrail
    does not skip the rest), but payload mutation and pipeline
    short-circuiting are applied in ``priority`` order: once any
    guardrail's action resolves to ``BLOCK``, evaluation of any
    remaining, lower-priority guardrails' *actions* is skipped and the
    call returns immediately with
    :attr:`~smarter.apps.guardrail.services.contracts.PipelineDisposition.BLOCKED`.
    Non-blocking triggers (``FLAG``, ``REDACT``, ``TRANSFORM``,
    ``ESCALATE``) accumulate across guardrails — later guardrails see
    the payload as mutated by earlier ones — and the final
    :attr:`~smarter.apps.guardrail.services.contracts.PipelineResult.disposition`
    reflects the most severe outcome reached, per the precedence
    ``ALLOWED < FLAGGED < REDACTED < TRANSFORMED < ESCALATED < BLOCKED``.

    A :class:`~smarter.apps.guardrail.models.Guardrail` row with
    ``is_blocking=False`` always runs in shadow mode: its finding is
    logged as if it triggered, but neither the payload nor the overall
    disposition is affected, regardless of its configured ``action``.

    :param account: The account whose Guardrail rows should be
        evaluated. Required — every pipeline call is scoped to exactly
        one account.
    :type account: ~smarter.apps.account.models.Account
    :param user_profile: If given, further restricts evaluation to
        Guardrail rows owned by this user profile within the account.
        If omitted (``None``), all of the account's active guardrails
        applicable to the stage are evaluated regardless of owning
        user profile.
    :type user_profile: ~smarter.apps.account.models.UserProfile or None

    :ivar account: The account this pipeline instance is scoped to, as
        passed to the constructor.
    :vartype account: ~smarter.apps.account.models.Account
    :ivar user_profile: The user profile this pipeline instance is
        scoped to, or ``None`` if unscoped.
    :vartype user_profile: ~smarter.apps.account.models.UserProfile or None

    .. note::
        A single :class:`GuardrailPipeline` instance is safe to reuse
        across multiple ``run_pre``/``run_post`` calls for the same
        account/user_profile scope — it holds no per-request state.
        Construct a new instance only when the scope changes.

    .. note::
        This class performs Django ORM queries (via
        :class:`~smarter.apps.guardrail.services.engine.GuardrailEngine`)
        and, depending on which
        :class:`~smarter.apps.guardrail.models.MatchStrategy` values are
        configured on the account's guardrails, may also invoke external
        embedding, classifier, or LLM-judge clients registered through
        :func:`~smarter.apps.guardrail.services.strategies.registry.configure_clients`.
        Both ``run_pre`` and ``run_post`` are therefore blocking, I/O-bound
        calls and should not be invoked from a hot inner loop without
        awareness of that cost.

    :Example:

    .. code-block:: python

        pipeline = GuardrailPipeline(
            account=harness.account,
            user_profile=harness.user_profile,
        )

        pre_result = pipeline.run_pre(pre_json, request_uid=request_uid)
        if pre_result.blocked:
            return error_response(pre_result.fallback_message)
        pre_json = pre_result.payload  # possibly redacted/transformed

        response_json = call_llm_provider(pre_json)

        post_result = pipeline.run_post(
            pre_json, response_json, request_uid=request_uid
        )
        if post_result.blocked:
            return error_response(post_result.fallback_message)
        response_json = post_result.payload

    .. seealso::
        :class:`~smarter.apps.guardrail.services.contracts.PipelineResult`
            The return type of both public methods.
        :class:`~smarter.apps.guardrail.services.engine.GuardrailEngine`
            Performs the underlying per-guardrail evaluation.
        :func:`~smarter.apps.guardrail.services.actions.apply_action`
            Applies a triggered guardrail's action to the payload.
        :class:`~smarter.apps.guardrail.models.Guardrail`
            The ORM model defining each guardrail rule.
    """

    def __init__(self, account: Account, user_profile: UserProfile | None = None):
        self.account = account
        self.user_profile = user_profile
        self._engine = GuardrailEngine(account=account, user_profile=user_profile)

    def run_pre(self, request_json: dict[str, Any], *, request_uid: str | None = None) -> PipelineResult:
        """Evaluate the pre-completion request against input guardrails.

        :param request_json: The request body about to be sent to the
            LLM provider.
        :type request_json: dict[str, typing.Any]
        :param request_uid: An optional caller-supplied identifier, used
            for correlating this evaluation with logs/traces and
            included on the returned result.
        :type request_uid: str or None
        :returns: The verdict for this request. Inspect
            :attr:`~smarter.apps.guardrail.services.contracts.PipelineResult.blocked`
            before proceeding, and use
            :attr:`~smarter.apps.guardrail.services.contracts.PipelineResult.payload`
            (which may differ from ``request_json`` if a guardrail
            redacted or transformed it) as the request actually sent
            onward.
        :rtype: ~smarter.apps.guardrail.services.contracts.PipelineResult
        """
        return self._run(payload=request_json, stage=GuardrailStage.PRE, request_uid=request_uid)

    def run_post(
        self,
        request_json: dict[str, Any],
        response_json: dict[str, Any],
        *,
        request_uid: str | None = None,
    ) -> PipelineResult:
        """Evaluate the post-completion response against output guardrails.

        :param request_json: The original request body, accepted for
            symmetry with :meth:`run_pre` and for future strategies that
            need the original prompt as context when judging the
            completion (e.g. an LLM-judge guardrail checking the
            response stayed on-topic relative to the question asked).
            The engine currently only scans ``response_json``.
        :type request_json: dict[str, typing.Any]
        :param response_json: The response body received from the LLM
            provider.
        :type response_json: dict[str, typing.Any]
        :param request_uid: An optional caller-supplied identifier, used
            for correlating this evaluation with logs/traces and
            included on the returned result.
        :type request_uid: str or None
        :returns: The verdict for this response. Inspect
            :attr:`~smarter.apps.guardrail.services.contracts.PipelineResult.blocked`
            before proceeding, and use
            :attr:`~smarter.apps.guardrail.services.contracts.PipelineResult.payload`
            (which may differ from ``response_json`` if a guardrail
            redacted or transformed it) as the response actually
            returned to the caller.
        :rtype: ~smarter.apps.guardrail.services.contracts.PipelineResult
        """
        # request_json is accepted for symmetry / future strategies that need
        # the original prompt as context when judging the completion (e.g. an
        # LLM-judge guardrail checking the response stayed on-topic relative
        # to the question asked). The engine currently only scans response_json.
        del request_json
        return self._run(payload=response_json, stage=GuardrailStage.POST, request_uid=request_uid)

    def _run(
        self,
        *,
        payload: dict[str, Any],
        stage: GuardrailStage,
        request_uid: str | None,
    ) -> PipelineResult:
        """Evaluate, act on, and fold outcomes for a single stage.

        :param payload: The payload to evaluate — a pre-completion
            request body or post-completion response body, depending on
            ``stage``.
        :type payload: dict[str, typing.Any]
        :param stage: Which side of the model call ``payload``
            represents.
        :type stage: ~smarter.apps.guardrail.services.contracts.GuardrailStage
        :param request_uid: An optional caller-supplied identifier,
            propagated to the engine and included on the returned
            result.
        :type request_uid: str or None
        :returns: The folded verdict across every guardrail evaluated
            for this stage.
        :rtype: ~smarter.apps.guardrail.services.contracts.PipelineResult
        """
        start = time.monotonic()
        outcomes = self._engine.run(payload=payload, stage=stage, request_uid=request_uid)

        working_payload = payload
        disposition = PipelineDisposition.ALLOWED
        fallback_message: str | None = None
        halted = False

        # GuardrailOutcome is a lightweight, serialization-friendly result
        # object and deliberately doesn't carry the full ORM row. apply_action()
        # needs a few live fields (is_blocking, action, config, fallback_message),
        # so fetch every referenced row once, up front, rather than per finding.
        triggered_ids = {o.guardrail_id for o in outcomes if o.triggered}
        guardrails_by_id = Guardrail.objects.in_bulk(triggered_ids) if triggered_ids else {}

        for outcome in sorted(outcomes, key=lambda o: o.priority):
            if halted:
                break
            guardrail = guardrails_by_id.get(outcome.guardrail_id)
            if guardrail is None:
                continue  # not triggered, or the row was deleted mid-flight

            for finding in outcome.findings:
                if not finding.triggered:
                    continue

                action_outcome: ActionOutcome = apply_action(
                    payload=working_payload,
                    finding=finding,
                    guardrail=guardrail,
                )
                working_payload = action_outcome.payload
                disposition = _fold(disposition, action_outcome.disposition)

                if action_outcome.fallback_message:
                    fallback_message = action_outcome.fallback_message

                if action_outcome.halt_pipeline:
                    halted = True
                    break

        total_duration_ms = (time.monotonic() - start) * 1000
        result = PipelineResult(
            stage=stage,
            disposition=disposition,
            payload=working_payload,
            fallback_message=fallback_message,
            outcomes=outcomes,
            guardrails_evaluated=len(outcomes),
            total_duration_ms=total_duration_ms,
            request_uid=request_uid,
        )

        logger.info(
            "GuardrailPipeline[%s] evaluated %d guardrail(s) in %.1fms -> disposition=%s",
            stage.value,
            len(outcomes),
            total_duration_ms,
            disposition.value,
        )
        return result


def _fold(current: PipelineDisposition, incoming: PipelineDisposition) -> PipelineDisposition:
    """Combine dispositions across multiple triggered guardrails.

    :param current: The disposition accumulated so far.
    :type current: ~smarter.apps.guardrail.services.contracts.PipelineDisposition
    :param incoming: The disposition just produced by the current
        guardrail's action.
    :type incoming: ~smarter.apps.guardrail.services.contracts.PipelineDisposition
    :returns: Whichever of ``current``/``incoming`` ranks higher in
        ``_DISPOSITION_PRECEDENCE``.
    :rtype: ~smarter.apps.guardrail.services.contracts.PipelineDisposition
    """
    if _DISPOSITION_PRECEDENCE.index(incoming) > _DISPOSITION_PRECEDENCE.index(current):
        return incoming
    return current


__all__ = ["GuardrailPipeline"]
