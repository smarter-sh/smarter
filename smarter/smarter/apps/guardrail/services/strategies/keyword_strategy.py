"""
``keyword``: ``guardrail.config["keywords"]`` is a list of words and phrases.

``guardrail.config["caseSensitive"]`` defaults to false, and ``guardrail.config["wholeWord"]``
to true. Whitespace within a phrase matches any whitespace, so that a phrase split across
lines still matches.
"""

import re
from functools import lru_cache

from smarter.apps.guardrail.services.exceptions import GuardrailConfigError
from smarter.apps.provider.services.text_completion.contracts import GuardrailMatch

from .base import BaseGuardrailStrategy, StrategyContext, StrategyMatch
from .detectors import MAX_MATCHES


@lru_cache(maxsize=512)
def compile_keywords(keywords: tuple[str, ...], case_sensitive: bool, whole_word: bool) -> re.Pattern:
    """Compile and cache a keyword list into a single alternation, longest keywords first."""
    escaped = [r"\s+".join(re.escape(word) for word in keyword.split()) for keyword in keywords]
    escaped.sort(key=len, reverse=True)
    body = "|".join(escaped)
    template = rf"(?<!\w)(?:{body})(?!\w)" if whole_word else f"(?:{body})"
    return re.compile(template, 0 if case_sensitive else re.IGNORECASE)


class KeywordStrategy(BaseGuardrailStrategy):
    """Match a text segment against a list of words and phrases."""

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """Find every occurrence of the Guardrail's keywords in the segment."""
        keywords = tuple(keyword.strip() for keyword in guardrail.settings.get("keywords") or [] if keyword.strip())
        if not keywords:
            raise GuardrailConfigError(f"Guardrail '{guardrail.name}' uses strategy keyword but has no keywords.")
        compiled = compile_keywords(
            keywords,
            bool(guardrail.settings.get("caseSensitive", False)),
            bool(guardrail.settings.get("wholeWord", True)),
        )
        matches = [
            GuardrailMatch(start=m.start(), end=m.end(), text=m.group(0), label=m.group(0).lower())
            for m in compiled.finditer(segment.text)
        ][:MAX_MATCHES]
        if not matches:
            return StrategyMatch(triggered=False)
        found = sorted({match.label for match in matches if match.label})
        return StrategyMatch(
            triggered=True, confidence=1.0, matches=matches, rationale=f"Matched the keywords: {', '.join(found)}."
        )


__all__ = ["KeywordStrategy", "compile_keywords"]
