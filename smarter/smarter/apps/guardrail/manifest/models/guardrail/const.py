"""Smarter API Guardrail Manifest Constants."""

from smarter.lib.journal.enum import SmarterJournalThings

MANIFEST_KIND = SmarterJournalThings.GUARDRAIL.value

DEFAULT_PRIORITY = 100
"""Default evaluation order of a Guardrail.

Lower runs first.
"""
DEFAULT_SEVERITY = 3
"""Default severity of a Guardrail, from 1 (low) to 5 (critical)."""
DEFAULT_REPLACEMENT = "[REDACTED]"
"""Default text that replaces the matches of a redact action."""
DEFAULT_MESSAGE = "This request was blocked by a guardrail."
"""Default user-facing message of a block action."""
DEFAULT_PROVIDER = "openai"
"""Default LLM provider of the semantic, moderation and llm_judge strategies."""
DEFAULT_JUDGE_MODEL = "gpt-4o-mini"
"""Default model of the llm_judge strategy."""
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
"""Default model of the semantic strategy."""
DEFAULT_MODERATION_MODEL = "omni-moderation-latest"
"""Default model of the moderation strategy."""
DEFAULT_THRESHOLD = 0.8
"""Default confidence threshold of the scored strategies."""

MAX_PATTERN_LENGTH = 4000
MAX_KEYWORDS = 500
MAX_REFERENCE_TEXTS = 50
MAX_JUDGE_PROMPT_LENGTH = 8000
MAX_MESSAGE_LENGTH = 1000
