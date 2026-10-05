"""Exceptions raised by the Guardrail service."""


class GuardrailServiceError(Exception):
    """Base class for all guardrail-service errors."""


class GuardrailConfigError(GuardrailServiceError):
    """
    Raised for a :class:`~smarter.apps.guardrail.models.Guardrail` whose configuration is invalid or incomplete for its strategy, e.g. ``strategy=regex`` without a ``pattern``.

    Manifests are validated when they are applied, so this indicates a Guardrail that was
    changed outside of a manifest, e.g. in the Django admin.
    """


class GuardrailStrategyNotImplementedError(GuardrailServiceError):
    """Raised when a Guardrail's strategy has no implementation."""


class GuardrailProviderError(GuardrailServiceError):
    """Raised when a strategy's call to an LLM provider fails, or returns an unusable result."""


class GuardrailBlockedError(GuardrailServiceError):
    """
    Raised by the prompt pipeline when an input guardrail blocks the user's message.

    :param message: The user-facing message to return instead of the LLM's reply.
    :param guardrail_name: The name of the guardrail that blocked the message.
    """

    def __init__(self, message: str, guardrail_name: str | None = None):
        self.message = message
        self.guardrail_name = guardrail_name
        super().__init__(message)


__all__ = [
    "GuardrailServiceError",
    "GuardrailConfigError",
    "GuardrailStrategyNotImplementedError",
    "GuardrailProviderError",
    "GuardrailBlockedError",
]
