"""``MatchStrategy.KEYWORD`` — ``guardrail.pattern`` is a newline- and/or.

comma-separated list of keywords/phrases.

Recognized ``guardrail.config`` keys:

* ``case_sensitive`` (``bool``) — defaults to ``False``.
* ``whole_word`` (``bool``) — defaults to ``True``, matching on word
  boundaries so e.g. ``"ass"`` doesn't match inside ``"assistant"``.
"""

from __future__ import annotations

import re
from functools import lru_cache

from smarter.apps.guardrail.services.exceptions import GuardrailConfigError
from smarter.apps.guardrail.services.strategies.base import (
    BaseGuardrailStrategy,
    StrategyContext,
    StrategyMatch,
)


def _split_keywords(pattern: str) -> list[str]:
    """Split a newline/comma-separated keyword list into individual terms.

    :param pattern: The raw ``guardrail.pattern`` string.
    :type pattern: str
    :returns: The non-empty, whitespace-trimmed keywords found in
        ``pattern``.
    :rtype: list[str]
    """
    raw = re.split(r"[\n,]+", pattern)
    return [kw.strip() for kw in raw if kw.strip()]


@lru_cache(maxsize=512)
def _compile_keyword_pattern(pattern: str, case_sensitive: bool, whole_word: bool) -> re.Pattern:
    """Compile and cache a keyword list into a single alternation regex.

    :param pattern: The raw ``guardrail.pattern`` string.
    :type pattern: str
    :param case_sensitive: Whether matching should be case-sensitive.
    :type case_sensitive: bool
    :param whole_word: Whether to anchor matches on word boundaries.
    :type whole_word: bool
    :returns: The compiled alternation pattern.
    :rtype: re.Pattern
    :raises smarter.apps.guardrail.services.exceptions.GuardrailConfigError:
        If ``pattern`` contains no usable keywords.
    """
    keywords = _split_keywords(pattern)
    if not keywords:
        raise GuardrailConfigError("Keyword guardrail pattern contained no usable keywords.")

    escaped = [re.escape(kw) for kw in sorted(keywords, key=len, reverse=True)]
    body = "|".join(escaped)
    template = rf"\b(?:{body})\b" if whole_word else f"(?:{body})"
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(template, flags)


class KeywordStrategy(BaseGuardrailStrategy):
    """Match a text segment against a literal keyword/phrase list."""

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Search ``segment.text`` for any keyword in ``guardrail.pattern``.

        :param segment: The text segment to evaluate.
        :type segment: ~smarter.apps.guardrail.services.contracts.TextSegment
        :param guardrail: The guardrail row; requires a non-empty
            ``pattern`` containing at least one keyword.
        :type guardrail: ~smarter.apps.guardrail.models.Guardrail
        :param context: Ambient evaluation context (unused by this
            strategy).
        :type context: ~smarter.apps.guardrail.services.strategies.base.StrategyContext
        :returns: A match with ``confidence=1.0`` and the matched
            keyword, or ``triggered=False`` if no keyword matches.
        :rtype: ~smarter.apps.guardrail.services.strategies.base.StrategyMatch
        :raises smarter.apps.guardrail.services.exceptions.GuardrailConfigError:
            If ``guardrail.pattern`` is empty or contains no usable
            keywords.
        """
        if not guardrail.pattern:
            raise GuardrailConfigError(
                f"Guardrail '{guardrail.name}' uses match_strategy=keyword but has no pattern set."
            )

        case_sensitive = bool(guardrail.config.get("case_sensitive", False))
        whole_word = bool(guardrail.config.get("whole_word", True))
        compiled = _compile_keyword_pattern(guardrail.pattern, case_sensitive, whole_word)

        match = compiled.search(segment.text)
        if not match:
            return StrategyMatch(triggered=False)

        return StrategyMatch(
            triggered=True,
            confidence=1.0,
            matched_text=match.group(0),
            rationale=f"Matched keyword '{match.group(0)}'",
        )


__all__ = ["KeywordStrategy"]
