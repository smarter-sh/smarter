"""Maps :class:`smarter.apps.guardrail.models.MatchStrategy` to a.

strategy instance.

Binary strategies (``regex``, ``keyword``) are stateless and
instantiated eagerly. Scored strategies (``semantic``, ``model``,
``llm_judge``) need an injected client, so they're built lazily the
first time they're requested, using whatever's been registered via
:func:`configure_clients`. Call :func:`configure_clients` once at app
startup (e.g. ``AppConfig.ready()``) with your concrete adapters; see
:mod:`smarter.apps.guardrail.services.strategies.clients` for the
protocols to implement.
"""

from smarter.apps.guardrail.models import MatchStrategy
from smarter.apps.guardrail.services.exceptions import (
    GuardrailStrategyNotImplementedError,
)
from smarter.apps.guardrail.services.strategies.base import BaseGuardrailStrategy
from smarter.apps.guardrail.services.strategies.clients import (
    ClassifierClient,
    EmbeddingClient,
    LLMJudgeClient,
)
from smarter.apps.guardrail.services.strategies.keyword_strategy import KeywordStrategy
from smarter.apps.guardrail.services.strategies.llm_judge_strategy import (
    LLMJudgeStrategy,
)
from smarter.apps.guardrail.services.strategies.model_strategy import (
    ModelStrategy,
)
from smarter.apps.guardrail.services.strategies.regex_strategy import RegexStrategy
from smarter.apps.guardrail.services.strategies.semantic_strategy import (
    SemanticStrategy,
)

_embedding_client: EmbeddingClient | None = None
_classifier_client: ClassifierClient | None = None
_judge_client: LLMJudgeClient | None = None

_eager_registry: dict[str, BaseGuardrailStrategy] = {
    MatchStrategy.REGEX: RegexStrategy(),
    MatchStrategy.KEYWORD: KeywordStrategy(),
}


def configure_clients(
    *,
    embedding_client: EmbeddingClient | None = None,
    classifier_client: ClassifierClient | None = None,
    judge_client: LLMJudgeClient | None = None,
) -> None:
    """Register concrete client adapters for the scored strategies.

    Call once at startup. Passing ``None`` for a client leaves it
    unconfigured — guardrails that need it will raise
    :class:`~smarter.apps.guardrail.services.exceptions.GuardrailStrategyNotImplementedError`
    at evaluation time rather than at startup, so unrelated guardrails
    keep working.

    :param embedding_client: The adapter used by
        :class:`~smarter.apps.guardrail.services.strategies.semantic_strategy.SemanticStrategy`.
    :type embedding_client: ~smarter.apps.guardrail.services.strategies.clients.EmbeddingClient or None
    :param classifier_client: The adapter used by
        :class:`~smarter.apps.guardrail.services.strategies.model_strategy.ModelStrategy`.
    :type classifier_client: ~smarter.apps.guardrail.services.strategies.clients.ClassifierClient or None
    :param judge_client: The adapter used by
        :class:`~smarter.apps.guardrail.services.strategies.llm_judge_strategy.LLMJudgeStrategy`.
    :type judge_client: ~smarter.apps.guardrail.services.strategies.clients.LLMJudgeClient or None
    :returns: None.
    :rtype: None
    """
    global _embedding_client, _classifier_client, _judge_client
    if embedding_client is not None:
        _embedding_client = embedding_client
    if classifier_client is not None:
        _classifier_client = classifier_client
    if judge_client is not None:
        _judge_client = judge_client


def get_strategy(match_strategy: str) -> BaseGuardrailStrategy:
    """Return the strategy instance for a ``MatchStrategy`` value.

    :param match_strategy: One of
        :class:`smarter.apps.guardrail.models.MatchStrategy`'s values.
    :type match_strategy: str
    :returns: The strategy instance to evaluate against.
    :rtype: ~smarter.apps.guardrail.services.strategies.base.BaseGuardrailStrategy
    :raises smarter.apps.guardrail.services.exceptions.GuardrailStrategyNotImplementedError:
        If ``match_strategy`` is unrecognized, or is a scored strategy
        whose client hasn't been configured yet via
        :func:`configure_clients`.
    """
    if match_strategy in _eager_registry:
        return _eager_registry[match_strategy]

    if match_strategy == MatchStrategy.SEMANTIC:
        if _embedding_client is None:
            raise GuardrailStrategyNotImplementedError(
                "match_strategy=semantic requires an EmbeddingClient — call "
                "strategies.registry.configure_clients(embedding_client=...) at startup."
            )

        return SemanticStrategy(_embedding_client)

    if match_strategy == MatchStrategy.MODEL:
        if _classifier_client is None:
            raise GuardrailStrategyNotImplementedError(
                "match_strategy=model requires a ClassifierClient — call "
                "strategies.registry.configure_clients(classifier_client=...) at startup."
            )

        return ModelStrategy(_classifier_client)

    if match_strategy == MatchStrategy.LLM_JUDGE:
        if _judge_client is None:
            raise GuardrailStrategyNotImplementedError(
                "match_strategy=llm_judge requires an LLMJudgeClient — call "
                "strategies.registry.configure_clients(judge_client=...) at startup."
            )

        return LLMJudgeStrategy(_judge_client)

    raise GuardrailStrategyNotImplementedError(f"No strategy registered for match_strategy='{match_strategy}'.")


__all__ = ["get_strategy", "configure_clients"]
