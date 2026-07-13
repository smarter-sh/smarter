"""Exceptions raised by the Guardrail service."""

from smarter.apps.guardrail.services.contracts import GuardrailFinding


class GuardrailServiceError(Exception):
    """Base class for all guardrail-service errors."""


class GuardrailConfigError(GuardrailServiceError):
    """Raised for a :class:`~smarter.apps.guardrail.models.Guardrail` row.

    with invalid or incomplete configuration for its
    :class:`~smarter.apps.guardrail.models.MatchStrategy`.

    For example, ``match_strategy=regex`` with an empty or invalid
    ``pattern``, or ``match_strategy=semantic`` missing
    ``config["reference_texts"]``.
    """


class GuardrailStrategyNotImplementedError(GuardrailServiceError):
    """Raised when a Guardrail references a ``match_strategy`` for which.

    no strategy class is registered in
    :mod:`smarter.apps.guardrail.services.strategies.registry`.
    """


class GuardrailBlockedError(GuardrailServiceError):
    """Raised internally to short-circuit execution when a blocking.

    guardrail fires with ``action=BLOCK``.

    Callers should generally prefer inspecting
    :attr:`~smarter.apps.guardrail.services.contracts.PipelineResult.disposition`
    over catching this — it exists mainly so action handlers can unwind
    cleanly out of the per-guardrail evaluation loop.

    :param finding: The finding that triggered the block.
    :type finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :param fallback_message: The user-facing message to surface. Falls
        back to a generic message if not given.
    :type fallback_message: str or None

    :ivar finding: The finding that triggered the block, as passed to
        the constructor.
    :vartype finding: ~smarter.apps.guardrail.services.contracts.GuardrailFinding
    :ivar fallback_message: The resolved user-facing message.
    :vartype fallback_message: str
    """

    def __init__(self, finding: GuardrailFinding, fallback_message: str | None = None):
        self.finding = finding
        self.fallback_message = fallback_message or "This request was blocked by a content guardrail."
        super().__init__(self.fallback_message)


__all__ = [
    "GuardrailServiceError",
    "GuardrailConfigError",
    "GuardrailStrategyNotImplementedError",
    "GuardrailBlockedError",
]
