"""Smarter API Budget Manifest Constants."""

from smarter.lib.journal.enum import SmarterJournalThings

MANIFEST_KIND = SmarterJournalThings.BUDGET.value

DEFAULT_WARNING_THRESHOLD = 80
"""Default percentage of a limit at which the budget_warning signal is sent."""
MAX_MESSAGE_LENGTH = 1000
MAX_RESOURCES = 1000
