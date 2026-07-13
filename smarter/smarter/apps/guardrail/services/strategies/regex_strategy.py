"""``MatchStrategy.REGEX`` — ``guardrail.pattern`` is a single Python regex.

Recognized ``guardrail.config`` keys:

* ``flags`` (``list[str]``) — any of ``"IGNORECASE"``, ``"MULTILINE"``,
  ``"DOTALL"``. Defaults to ``["IGNORECASE"]``.
"""

import re
from functools import lru_cache

from smarter.apps.guardrail.services.exceptions import GuardrailConfigError
from smarter.apps.guardrail.services.strategies.base import (
    BaseGuardrailStrategy,
    StrategyContext,
    StrategyMatch,
)

_FLAG_MAP = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
}


@lru_cache(maxsize=512)
def _compile(pattern: str, flags: tuple[str, ...]) -> re.Pattern:
    """Compile and cache a regex pattern with the given named flags.

    :param pattern: The regex pattern source.
    :type pattern: str
    :param flags: Flag names to apply, e.g. ``("IGNORECASE",)``.
    :type flags: tuple[str, ...]
    :returns: The compiled pattern.
    :rtype: re.Pattern
    :raises smarter.apps.guardrail.services.exceptions.GuardrailConfigError:
        If a flag name is unrecognized, or ``pattern`` fails to compile.
    """
    combined = 0
    for flag in flags:
        try:
            combined |= _FLAG_MAP[flag]
        except KeyError as exc:
            raise GuardrailConfigError(f"Unknown regex flag '{flag}'") from exc
    try:
        return re.compile(pattern, combined)
    except re.error as exc:
        raise GuardrailConfigError(f"Invalid regex pattern: {exc}") from exc


class RegexStrategy(BaseGuardrailStrategy):
    """Match a text segment against a single compiled regular expression."""

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Search ``segment.text`` for ``guardrail.pattern``.

        :param segment: The text segment to evaluate.
        :type segment: ~smarter.apps.guardrail.services.contracts.TextSegment
        :param guardrail: The guardrail row; requires a non-empty,
            compilable ``pattern``.
        :type guardrail: ~smarter.apps.guardrail.models.Guardrail
        :param context: Ambient evaluation context (unused by this
            strategy).
        :type context: ~smarter.apps.guardrail.services.strategies.base.StrategyContext
        :returns: A match with ``confidence=1.0`` and the first matched
            substring, or ``triggered=False`` if the pattern does not
            match.
        :rtype: ~smarter.apps.guardrail.services.strategies.base.StrategyMatch
        :raises smarter.apps.guardrail.services.exceptions.GuardrailConfigError:
            If ``guardrail.pattern`` is empty or fails to compile.
        """
        if not guardrail.pattern:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses match_strategy=regex but has no pattern set."
            )

        flags = tuple(guardrail.config.get("flags", ["IGNORECASE"]))
        compiled = _compile(guardrail.pattern, flags)
        match = compiled.search(segment.text)

        if not match:
            return StrategyMatch(triggered=False)

        return StrategyMatch(
            triggered=True,
            confidence=1.0,
            matched_text=match.group(0),
            rationale=f"Matched regex pattern at span {match.span()}",
        )


__all__ = ["RegexStrategy"]
