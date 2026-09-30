"""
The runtime of the Guardrail service.

The prompt pipeline calls :class:`~smarter.apps.guardrail.services.pipeline.GuardrailPipeline`
to run an LLMClient's guardrails on the user's message and the LLM's reply. Everything else
(``engine``, ``strategies``, ``actions``, ``events`` and ``text_extraction``) is its
implementation.
"""

from smarter.apps.guardrail.services.exceptions import (
    GuardrailBlockedError,
    GuardrailConfigError,
    GuardrailProviderError,
    GuardrailServiceError,
    GuardrailStrategyNotImplementedError,
)
from smarter.apps.guardrail.services.pipeline import GuardrailPipeline
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailFinding,
    GuardrailMatch,
    GuardrailOutcome,
    GuardrailStage,
    PipelineDisposition,
    PipelineResult,
)

__all__ = [
    "GuardrailPipeline",
    "PipelineResult",
    "PipelineDisposition",
    "GuardrailStage",
    "GuardrailOutcome",
    "GuardrailFinding",
    "GuardrailMatch",
    "GuardrailServiceError",
    "GuardrailConfigError",
    "GuardrailProviderError",
    "GuardrailStrategyNotImplementedError",
    "GuardrailBlockedError",
]
