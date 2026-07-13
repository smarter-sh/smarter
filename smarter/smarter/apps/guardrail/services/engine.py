"""Load and evaluate guardrails for a given account/user_profile scope.

:class:`GuardrailEngine` loads the ordered, active
:class:`~smarter.apps.guardrail.models.Guardrail` rows for an
account/user_profile and runs each against every scannable segment of a
payload, producing :class:`~smarter.apps.guardrail.services.contracts.GuardrailOutcome`
objects. It knows nothing about the Harness or HTTP —
:class:`~smarter.apps.guardrail.services.pipeline.GuardrailPipeline` is
the thing that wraps this into the pre/post contract the Harness
actually calls.
"""

from __future__ import annotations

import time
from typing import Any

from smarter.apps.account.models import UserProfile
from smarter.apps.guardrail.caching import (
    get_cached_guardrails_available_to_user_profile,
)
from smarter.apps.guardrail.models import Guardrail, GuardrailType
from smarter.apps.guardrail.services.contracts import (
    GuardrailFinding,
    GuardrailOutcome,
    GuardrailStage,
    TextSegment,
)
from smarter.apps.guardrail.services.exceptions import (
    GuardrailConfigError,
    GuardrailStrategyNotImplementedError,
)
from smarter.apps.guardrail.services.strategies.base import StrategyContext
from smarter.apps.guardrail.services.strategies.registry import get_strategy
from smarter.apps.guardrail.services.text_extraction import extract_segments
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])

_STAGE_TO_TYPES = {
    GuardrailStage.PRE: (GuardrailType.INPUT, GuardrailType.BOTH),
    GuardrailStage.POST: (GuardrailType.OUTPUT, GuardrailType.BOTH),
}


class GuardrailEngine:
    """Evaluate an account's guardrails against a payload's text segments.

    Stateless with respect to individual requests — construct one per
    :class:`~smarter.apps.account.models.Account`/
    :class:`~smarter.apps.account.models.UserProfile` scope (cheap; the
    query is re-issued per call, see :meth:`load_guardrails`) and call
    :meth:`run` for every pre/post payload in that scope.

    :param account: The account whose guardrails should be evaluated.
    :type account: ~smarter.apps.account.models.Account
    :param user_profile: If given, further restricts evaluation to
        guardrails owned by this user profile within the account.
    :type user_profile: ~smarter.apps.account.models.UserProfile or None

    :ivar account: The account this engine instance is scoped to.
    :vartype account: ~smarter.apps.account.models.Account
    :ivar user_profile: The user profile this engine instance is scoped
        to, or ``None`` if unscoped.
    :vartype user_profile: ~smarter.apps.account.models.UserProfile or None
    """

    def __init__(self, user_profile: UserProfile | None = None):
        self.user_profile = user_profile

    def load_guardrails(self, stage: GuardrailStage) -> list[Guardrail]:
        """Return the active guardrails applicable to ``stage``.

        .. note::
            :class:`~smarter.apps.account.models.MetaDataWithOwnershipModel`'s
            account/user_profile scoping follows the same convention as
            every other resource type on the platform (see
            ``LLMClient``, ``Vectorsearch``, etc.) — adjust the filter
            kwargs here if ``Guardrail``'s actual FK names differ.

        :param stage: Which side of the model call to load guardrails
            for. Rows with ``guardrail_type=BOTH`` are included for
            either stage.
        :type stage: ~smarter.apps.guardrail.services.contracts.GuardrailStage
        :returns: Active, applicable guardrails scoped to this engine's
            account/user_profile, ordered by ``priority`` (lower runs
            first) then ``id``.
        :rtype: list[~smarter.apps.guardrail.models.Guardrail]
        """

        applicable_types = _STAGE_TO_TYPES[stage]
        queryset = get_cached_guardrails_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
        queryset = queryset.filter(guardrail_type__in=applicable_types)

        return list(queryset.order_by("priority", "id"))

    def run(
        self,
        *,
        payload: dict[str, Any],
        stage: GuardrailStage,
        request_uid: str | None = None,
    ) -> list[GuardrailOutcome]:
        """Evaluate every applicable guardrail against every segment.

        Does **not** apply actions or short-circuit on block — that is
        the pipeline's responsibility, since only it knows how to
        compose outcomes across guardrails into a single disposition.

        :param payload: The pre-completion request body or
            post-completion response body to evaluate.
        :type payload: dict[str, typing.Any]
        :param stage: Which side of the model call ``payload``
            represents.
        :type stage: ~smarter.apps.guardrail.services.contracts.GuardrailStage
        :param request_uid: An optional caller-supplied identifier,
            threaded through to :class:`~smarter.apps.guardrail.services.strategies.base.StrategyContext`
            for correlating strategy calls with a specific request.
        :type request_uid: str or None
        :returns: One outcome per applicable, active guardrail, in
            priority order.
        :rtype: list[~smarter.apps.guardrail.services.contracts.GuardrailOutcome]
        """
        segments = extract_segments(payload, stage)
        guardrails = self.load_guardrails(stage)

        outcomes: list[GuardrailOutcome] = []
        context = StrategyContext(
            stage=stage,
            account_id=self.account.id,  # type: ignore
            user_profile_id=self.user_profile.id if self.user_profile else None,  # type: ignore
            request_uid=request_uid,
        )

        for guardrail in guardrails:
            outcomes.append(self._run_one(guardrail, segments, context))

        return outcomes

    def _run_one(
        self,
        guardrail: Guardrail,
        segments: list[TextSegment],
        context: StrategyContext,
    ) -> GuardrailOutcome:
        """Evaluate a single guardrail against every given segment.

        Any exception raised while resolving or running the guardrail's
        strategy is caught and recorded on the returned outcome's
        ``error`` field rather than propagated — a single
        misconfigured or failing guardrail must not take down the rest
        of the pipeline.

        :param guardrail: The guardrail row to evaluate.
        :type guardrail: ~smarter.apps.guardrail.models.Guardrail
        :param segments: The text segments to scan.
        :type segments: list[~smarter.apps.guardrail.services.contracts.TextSegment]
        :param context: Ambient evaluation context passed to the
            strategy.
        :type context: ~smarter.apps.guardrail.services.strategies.base.StrategyContext
        :returns: The outcome of evaluating ``guardrail`` against every
            segment in ``segments``.
        :rtype: ~smarter.apps.guardrail.services.contracts.GuardrailOutcome
        """
        start = time.monotonic()
        findings: list[GuardrailFinding] = []
        error: str | None = None

        try:
            strategy = get_strategy(guardrail.match_strategy)
            for segment in segments:
                match = strategy.evaluate(segment=segment, guardrail=guardrail, context=context)
                if match.triggered and not strategy.meets_threshold(guardrail, match.confidence):
                    continue
                findings.append(
                    GuardrailFinding(
                        guardrail_id=guardrail.id,  # type: ignore
                        guardrail_name=guardrail.name,
                        category=guardrail.category,
                        match_strategy=guardrail.match_strategy,
                        action=guardrail.action,
                        severity=guardrail.severity,
                        triggered=match.triggered,
                        confidence=match.confidence,
                        matched_text=match.matched_text,
                        segment_path=segment.path if match.triggered else None,
                        rationale=match.rationale,
                    )
                )
        except (GuardrailConfigError, GuardrailStrategyNotImplementedError) as exc:
            error = str(exc)
            logger.error("Guardrail '%s' failed to evaluate: %s", guardrail.name, error)
        # pylint: disable=broad-except
        except Exception as exc:  # noqa: BLE001 - a single bad guardrail must not take down the pipeline
            error = f"Unexpected error: {exc}"
            logger.error("Guardrail '%s' raised an unexpected error during evaluation.", guardrail.name)

        duration_ms = (time.monotonic() - start) * 1000
        return GuardrailOutcome(
            guardrail_id=guardrail.id,  # type: ignore
            guardrail_name=guardrail.name,
            is_blocking=guardrail.is_blocking,
            priority=guardrail.priority,
            findings=findings,
            error=error,
            duration_ms=duration_ms,
        )


__all__ = ["GuardrailEngine"]
