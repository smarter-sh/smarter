"""``MatchStrategy.LLM_JUDGE`` — ``guardrail.pattern`` is a judge prompt.

template containing a ``{text}`` placeholder; it's sent to an LLM which
is expected to return a structured triggered/confidence/rationale
verdict.

Recognized ``guardrail.config`` keys:

* ``model_id`` (``str``, required) — judge model to call.
* ``temperature`` (``float``, optional) — defaults to ``0.0`` to keep
  judges deterministic.

``guardrail.confidence_threshold`` gates the trigger; defaults to
:data:`_DEFAULT_THRESHOLD` if unset.
"""

from smarter.apps.guardrail.services.exceptions import GuardrailConfigError
from smarter.apps.guardrail.services.strategies.base import (
    BaseGuardrailStrategy,
    StrategyContext,
    StrategyMatch,
)
from smarter.apps.guardrail.services.strategies.clients import LLMJudgeClient

_DEFAULT_THRESHOLD = 0.7


class LLMJudgeStrategy(BaseGuardrailStrategy):
    """Match a text segment by delegating the judgment to an LLM.

    :param judge_client: The client used to run the rendered judge
        prompt.
    :type judge_client: ~smarter.apps.guardrail.services.strategies.clients.LLMJudgeClient
    """

    def __init__(self, judge_client: LLMJudgeClient):
        self._client = judge_client

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Render the judge prompt for ``segment.text`` and run it.

        :param segment: The text segment to evaluate.
        :type segment: ~smarter.apps.guardrail.services.contracts.TextSegment
        :param guardrail: The guardrail row; requires ``pattern`` to
            contain a ``{text}`` placeholder and ``config["model_id"]``
            to be set.
        :type guardrail: ~smarter.apps.guardrail.models.Guardrail
        :param context: Ambient evaluation context (unused by this
            strategy).
        :type context: ~smarter.apps.guardrail.services.strategies.base.StrategyContext
        :returns: A match with the judge's confidence, ``triggered``
            when the judge reports ``triggered=True`` and its
            confidence meets ``guardrail.confidence_threshold``.
        :rtype: ~smarter.apps.guardrail.services.strategies.base.StrategyMatch
        :raises smarter.apps.guardrail.services.exceptions.GuardrailConfigError:
            If ``guardrail.pattern`` is empty, lacks a ``{text}``
            placeholder, or ``guardrail.config["model_id"]`` is unset.
        """
        if not guardrail.pattern or "{text}" not in guardrail.pattern:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses match_strategy=llm_judge but `pattern` "
                "is empty or missing a {text} placeholder."
            )

        model_id = guardrail.config.get("model_id")
        if not model_id:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses match_strategy=llm_judge but config.model_id is unset."
            )

        temperature = float(guardrail.config.get("temperature", 0.0))
        prompt = guardrail.pattern.format(text=segment.text)

        verdict = self._client.judge(prompt, model_id=model_id, temperature=temperature)
        threshold = guardrail.confidence_threshold or _DEFAULT_THRESHOLD

        triggered = verdict.triggered and verdict.confidence >= threshold
        return StrategyMatch(
            triggered=triggered,
            confidence=verdict.confidence,
            matched_text=segment.text if triggered else None,
            rationale=verdict.rationale or "LLM judge did not provide a rationale.",
        )


__all__ = ["LLMJudgeStrategy"]
