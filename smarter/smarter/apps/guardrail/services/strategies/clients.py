"""Protocols for the external calls the scored strategies need to make.

The ``semantic``, ``model``, and ``llm_judge`` strategies each need an
external call — embeddings, a classifier model, or an LLM judge,
respectively. These are intentionally left as injectable interfaces
rather than hardcoded to a specific provider: the platform already has
``LLMClient``/``Vectorsearch`` resources for exactly this kind of call,
and the concrete adapters belong in a follow-up
(``GuardrailEmbeddingAdapter``, ``GuardrailClassifierAdapter``,
``GuardrailJudgeAdapter``) that wraps those resources rather than
reinventing provider plumbing here.

Wire a concrete implementation via
:func:`smarter.apps.guardrail.services.strategies.registry.configure_clients`
at app startup (e.g. in ``AppConfig.ready()``). Until that's wired,
strategies that need a client raise
:class:`~smarter.apps.guardrail.services.exceptions.GuardrailStrategyNotImplementedError`
with a clear message rather than silently no-op'ing — a guardrail that
can't actually run should never be mistaken for one that ran and
passed.
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingClient(Protocol):
    """Used by :class:`~smarter.apps.guardrail.services.strategies.semantic_strategy.SemanticStrategy`.

    to compare a segment against reference texts.
    """

    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for ``text``.

        :param text: The text to embed.
        :type text: str
        :returns: The embedding vector.
        :rtype: list[float]
        """
        ...


class ClassifierClient(Protocol):
    """Used by :class:`~smarter.apps.guardrail.services.strategies.model_strategy.ModelStrategy`.

    to run a segment through a hosted/local classifier model (e.g. a
    moderation or PII-detection model).
    """

    def classify(self, text: str, *, model_id: str) -> ClassifierVerdict:
        """Classify ``text`` using the given model.

        :param text: The text to classify.
        :type text: str
        :param model_id: Identifier of the classifier model to use.
        :type model_id: str
        :returns: The classifier's verdict.
        :rtype: ClassifierVerdict
        """
        ...


class ClassifierVerdict:
    """The result of a single :meth:`ClassifierClient.classify` call.

    :param label: The predicted label.
    :type label: str
    :param confidence: The model's confidence in ``label``, in
        ``[0.0, 1.0]``.
    :type confidence: float

    :ivar label: The predicted label, as passed to the constructor.
    :vartype label: str
    :ivar confidence: The model's confidence, as passed to the
        constructor.
    :vartype confidence: float
    """

    __slots__ = ("label", "confidence")

    def __init__(self, label: str, confidence: float):
        self.label = label
        self.confidence = confidence


class LLMJudgeClient(Protocol):
    """Used by :class:`~smarter.apps.guardrail.services.strategies.llm_judge_strategy.LLMJudgeStrategy`.

    to run a judge prompt against an LLM and get back a structured
    verdict.
    """

    def judge(self, prompt: str, *, model_id: str, temperature: float = 0.0) -> JudgeVerdict:
        """Run a judge prompt against an LLM.

        :param prompt: The fully-rendered judge prompt (i.e. the
            guardrail's ``pattern`` template with ``{text}`` already
            substituted).
        :type prompt: str
        :param model_id: Identifier of the judge model to use.
        :type model_id: str
        :param temperature: Sampling temperature for the judge call.
            Defaults to ``0.0`` to keep judge verdicts deterministic.
        :type temperature: float
        :returns: The judge's structured verdict.
        :rtype: JudgeVerdict
        """
        ...


class JudgeVerdict:
    """The result of a single :meth:`LLMJudgeClient.judge` call.

    :param triggered: Whether the judge considered the guardrail
        condition met.
    :type triggered: bool
    :param confidence: The judge's confidence in ``triggered``, in
        ``[0.0, 1.0]``.
    :type confidence: float
    :param rationale: The judge's explanation for its verdict.
    :type rationale: str

    :ivar triggered: Whether the guardrail condition was met, as passed
        to the constructor.
    :vartype triggered: bool
    :ivar confidence: The judge's confidence, as passed to the
        constructor.
    :vartype confidence: float
    :ivar rationale: The judge's explanation, as passed to the
        constructor.
    :vartype rationale: str
    """

    __slots__ = ("triggered", "confidence", "rationale")

    def __init__(self, triggered: bool, confidence: float, rationale: str = ""):
        self.triggered = triggered
        self.confidence = confidence
        self.rationale = rationale


__all__ = [
    "EmbeddingClient",
    "ClassifierClient",
    "ClassifierVerdict",
    "LLMJudgeClient",
    "JudgeVerdict",
]
