"""
``regex``: ``guardrail.pattern`` is a single Python regular expression.

``guardrail.config["flags"]`` may contain any of ``IGNORECASE``, ``MULTILINE`` and ``DOTALL``.
It defaults to ``["IGNORECASE"]``.
"""

import re
from functools import lru_cache

from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.services.exceptions import GuardrailConfigError
from smarter.apps.provider.services.text_completion.contracts import GuardrailMatch

from .base import BaseGuardrailStrategy, StrategyContext, StrategyMatch
from .detectors import MAX_MATCHES

FLAGS = {"IGNORECASE": re.IGNORECASE, "MULTILINE": re.MULTILINE, "DOTALL": re.DOTALL}


@lru_cache(maxsize=512)
def compile_pattern(pattern: str, flags: tuple[str, ...]) -> re.Pattern:
    """
    Compile and cache a regex pattern with the given named flags.

    :raises GuardrailConfigError: If a flag is unknown, or the pattern does not compile.
    """
    combined = 0
    for flag in flags:
        try:
            combined |= FLAGS[flag]
        except KeyError as e:
            raise GuardrailConfigError(f"Unknown regex flag '{flag}'") from e
    try:
        return re.compile(pattern, combined)
    except re.error as e:
        raise GuardrailConfigError(f"Invalid regex pattern: {e}") from e


def compiled_pattern(guardrail: Guardrail) -> re.Pattern:
    """Return the Guardrail's compiled pattern."""
    if not guardrail.pattern:
        raise GuardrailConfigError(f"Guardrail '{guardrail.name}' uses strategy regex but has no pattern.")
    flags = guardrail.settings.get("flags")
    return compile_pattern(guardrail.pattern, tuple(["IGNORECASE"] if flags is None else flags))


class RegexStrategy(BaseGuardrailStrategy):
    """Match a text segment against a regular expression."""

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Find every match of ``guardrail.pattern`` in the segment."""
        matches = [
            GuardrailMatch(start=m.start(), end=m.end(), text=m.group(0))
            for m in compiled_pattern(guardrail).finditer(segment.text)
            if m.end() > m.start()
        ][:MAX_MATCHES]
        if not matches:
            return StrategyMatch(triggered=False)
        return StrategyMatch(
            triggered=True,
            confidence=1.0,
            matches=matches,
            rationale=f"Matched the regular expression {len(matches)} time(s).",
        )


__all__ = ["RegexStrategy", "compile_pattern", "compiled_pattern"]
