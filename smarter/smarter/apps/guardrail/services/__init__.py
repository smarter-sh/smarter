"""Runtime pipeline for the Guardrail service.

The Harness calls into this package to evaluate an indefinite number
of :class:`~smarter.apps.guardrail.models.Guardrail` rows against a
pre-completion request and/or post-completion response, in priority
order, folding their outcomes into a single verdict.

Public surface:

* :class:`~smarter.apps.guardrail.services.pipeline.GuardrailPipeline`
  — the Harness-facing entry point.
* :class:`~smarter.apps.guardrail.services.contracts.PipelineResult`
  — what ``run_pre()``/``run_post()`` return.
* :class:`~smarter.apps.guardrail.services.exceptions.GuardrailBlockedError`
  — raised internally, rarely needed by callers.

Everything else (``engine``, ``strategies``, ``actions``,
``text_extraction``) is implementation detail the Harness shouldn't
need to import directly.
"""

from smarter.apps.guardrail.services.contracts import (
    GuardrailFinding,
    GuardrailOutcome,
    GuardrailStage,
    PipelineDisposition,
    PipelineResult,
)
from smarter.apps.guardrail.services.exceptions import (
    GuardrailBlockedError,
    GuardrailConfigError,
    GuardrailServiceError,
    GuardrailStrategyNotImplementedError,
)
from smarter.apps.guardrail.services.pipeline import GuardrailPipeline

__all__ = [
    "GuardrailPipeline",
    "PipelineResult",
    "PipelineDisposition",
    "GuardrailStage",
    "GuardrailOutcome",
    "GuardrailFinding",
    "GuardrailServiceError",
    "GuardrailConfigError",
    "GuardrailStrategyNotImplementedError",
    "GuardrailBlockedError",
]
