"""
Maps each :class:`~smarter.apps.guardrail.models.GuardrailStrategy` to its strategy.

The strategies are stateless singletons. The scored strategies get their client from
:func:`~.clients.get_client` when they evaluate, so that each Guardrail may name its own
provider. :func:`~.clients.configure_clients`, re-exported here, replaces the client factory,
e.g. with a fake in tests.
"""

from smarter.apps.guardrail.models import GuardrailStrategy
from smarter.apps.guardrail.services.exceptions import (
    GuardrailStrategyNotImplementedError,
)

from .base import BaseGuardrailStrategy
from .clients import configure_clients, get_client
from .detector_strategy import DetectorStrategy
from .keyword_strategy import KeywordStrategy
from .llm_judge_strategy import LLMJudgeStrategy
from .moderation_strategy import ModerationStrategy
from .regex_strategy import RegexStrategy
from .semantic_strategy import SemanticStrategy

_STRATEGIES: dict[str, BaseGuardrailStrategy] = {
    GuardrailStrategy.REGEX: RegexStrategy(),
    GuardrailStrategy.KEYWORD: KeywordStrategy(),
    GuardrailStrategy.DETECTOR: DetectorStrategy(),
    GuardrailStrategy.SEMANTIC: SemanticStrategy(),
    GuardrailStrategy.MODERATION: ModerationStrategy(),
    GuardrailStrategy.LLM_JUDGE: LLMJudgeStrategy(),
}


def get_strategy(strategy: str) -> BaseGuardrailStrategy:
    """
    Return the strategy for a :class:`~smarter.apps.guardrail.models.GuardrailStrategy` value.

    :raises GuardrailStrategyNotImplementedError: If the strategy is unknown.
    """
    try:
        return _STRATEGIES[strategy]
    except KeyError as e:
        raise GuardrailStrategyNotImplementedError(f"No strategy is registered for '{strategy}'.") from e


__all__ = ["configure_clients", "get_client", "get_strategy"]
