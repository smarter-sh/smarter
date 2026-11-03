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
    """
    Compile and cache a keyword list into a single alternation, longest keywords first.

    :param keywords: The keywords and phrases. A tuple, so that it can be cached.
    :param case_sensitive: Whether matching is case sensitive.
    :param whole_word: Whether a keyword must not be preceded or followed by a word character.
    :returns: The compiled pattern. Whitespace within a phrase matches any whitespace.
    """
    escaped = []
    for keyword in keywords:
        escaped_words = [re.escape(word) for word in keyword.split()]
        escaped.append(r"\s+".join(escaped_words))
    escaped.sort(key=len, reverse=True)
    body = "|".join(escaped)
    if whole_word:
        template = rf"(?<!\w)(?:{body})(?!\w)"
    else:
        template = f"(?:{body})"
    if case_sensitive:
        flags = 0
    else:
        flags = re.IGNORECASE
    return re.compile(template, flags)


class KeywordStrategy(BaseGuardrailStrategy):
    """Match a text segment against a list of words and phrases."""

    def evaluate(self, *, segment, guardrail, context: StrategyContext) -> StrategyMatch:
        """
        Find every occurrence of the Guardrail's keywords in the segment.

        :param segment: The text segment.
        :param guardrail: The Guardrail, which supplies the strategy's configuration.
        :param context: Ambient evaluation context. Unused.
        :returns: A triggered match, with at most ``MAX_MATCHES`` matches, or an untriggered one.
        :raises GuardrailConfigError: when the Guardrail has no keywords.
        """
        configured_keywords = guardrail.settings.get("keywords") or []
        stripped_keywords = []
        for keyword in configured_keywords:
            stripped = keyword.strip()
            if stripped:
                stripped_keywords.append(stripped)
        keywords = tuple(stripped_keywords)
        if not keywords:
            raise GuardrailConfigError(f"Guardrail '{guardrail.name}' uses strategy keyword but has no keywords.")
        compiled = compile_keywords(
            keywords,
            bool(guardrail.settings.get("caseSensitive", False)),
            bool(guardrail.settings.get("wholeWord", True)),
        )
        all_matches = []
        for m in compiled.finditer(segment.text):
            matched_text = m.group(0)
            all_matches.append(
                GuardrailMatch(start=m.start(), end=m.end(), text=matched_text, label=matched_text.lower())
            )
        matches = all_matches[:MAX_MATCHES]
        if not matches:
            return StrategyMatch(triggered=False)
        found = sorted({match.label for match in matches if match.label})
        return StrategyMatch(
            triggered=True, confidence=1.0, matches=matches, rationale=f"Matched the keywords: {', '.join(found)}."
        )


__all__ = ["KeywordStrategy", "compile_keywords"]
