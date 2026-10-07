"""
Test :mod:`smarter.apps.guardrail.services.actions`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.guardrail.manifest.models.guardrail.const import (
    DEFAULT_MESSAGE,
    DEFAULT_REPLACEMENT,
)
from smarter.apps.guardrail.models import Guardrail, GuardrailDisposition
from smarter.apps.guardrail.services.actions import apply_action, replace_matches
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailFinding,
    GuardrailMatch,
    PipelineDisposition,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import input_payload

TEXT = "call 555-0101 or 555-0202 now"
PATH = "messages[1].content"


def finding(matches=None, action="redact") -> GuardrailFinding:
    """Return a finding of the two phone numbers in TEXT."""
    if matches is None:
        matches = [
            GuardrailMatch(start=5, end=13, text="555-0101", label="phone"),
            GuardrailMatch(start=17, end=25, text="555-0202", label="phone"),
        ]
    return GuardrailFinding(
        guardrail_id=1,
        guardrail_name="test",
        category="pii",
        strategy="regex",
        action=action,
        severity=3,
        triggered=True,
        confidence=1.0,
        matches=matches,
        segment_path=PATH,
    )


def guardrail(action: str, **fields) -> Guardrail:
    """Return an unsaved regex Guardrail that matches the phone numbers in TEXT."""
    data = {
        "name": "test",
        "strategy": "regex",
        "pattern": r"555-(\d{4})",
        "config": {},
        "mode": "enforce",
        "action": action,
    }
    data.update(fields)
    return Guardrail(**data)


def run(action: str, **fields):
    """Apply an action to TEXT."""
    return apply_action(
        payload=input_payload(TEXT), finding=finding(action=action), guardrail=guardrail(action, **fields)
    )


def content(outcome) -> str:
    """Return the user message of an outcome's payload."""
    return outcome.payload["messages"][1]["content"]


class TestGuardrailActions(SmarterTestBase):
    """Test each action, and monitor mode."""

    def test_log_flag_escalate(self):
        """Test that log, flag and escalate leave the payload unchanged."""
        for action, disposition, event in (
            ("log", PipelineDisposition.ALLOWED, GuardrailDisposition.LOGGED),
            ("flag", PipelineDisposition.FLAGGED, GuardrailDisposition.FLAGGED),
            ("escalate", PipelineDisposition.ESCALATED, GuardrailDisposition.ESCALATED),
        ):
            with self.subTest(action=action):
                outcome = run(action)
                self.assertEqual(content(outcome), TEXT)
                self.assertEqual(outcome.disposition, disposition)
                self.assertEqual(outcome.event_disposition, event)
                self.assertFalse(outcome.halt_pipeline)

    def test_redact_every_match(self):
        """Test that redact replaces every match, not just the first."""
        outcome = run("redact")
        self.assertEqual(content(outcome), f"call {DEFAULT_REPLACEMENT} or {DEFAULT_REPLACEMENT} now")
        self.assertEqual(outcome.disposition, PipelineDisposition.REDACTED)

    def test_redact_label(self):
        """Test that {label} in the replacement is what matched."""
        self.assertEqual(content(run("redact", replacement="<{label}>")), "call <phone> or <phone> now")

    def test_redact_without_matches_flags(self):
        """Test that redact without matches, e.g. from a scored strategy, flags instead."""
        outcome = apply_action(payload=input_payload(TEXT), finding=finding(matches=[]), guardrail=guardrail("redact"))
        self.assertEqual(outcome.disposition, PipelineDisposition.FLAGGED)
        self.assertEqual(content(outcome), TEXT)

    def test_transform_regex_groups(self):
        """Test that transform with the regex strategy may refer to the pattern's groups."""
        outcome = run("transform", replacement=r"555-XXXX(\1)")
        self.assertEqual(content(outcome), "call 555-XXXX(0101) or 555-XXXX(0202) now")
        self.assertEqual(outcome.disposition, PipelineDisposition.TRANSFORMED)

    def test_transform_literal(self):
        """Test that transform with another strategy replaces each match literally."""
        self.assertEqual(content(run("transform", strategy="keyword", replacement="#")), "call # or # now")

    def test_block(self):
        """Test that block halts the pipeline, with the guardrail's message, or the default."""
        outcome = run("block", message="Nope.")
        self.assertEqual(outcome.disposition, PipelineDisposition.BLOCKED)
        self.assertTrue(outcome.halt_pipeline)
        self.assertEqual(outcome.message, "Nope.")
        self.assertEqual(run("block").message, DEFAULT_MESSAGE)

    def test_monitor_mode(self):
        """Test that a guardrail in monitor mode never acts, and records that it would have."""
        for action in ("redact", "block", "transform"):
            with self.subTest(action=action):
                outcome = run(action, mode="monitor", replacement="x")
                self.assertEqual(content(outcome), TEXT)
                self.assertEqual(outcome.disposition, PipelineDisposition.ALLOWED)
                self.assertEqual(outcome.event_disposition, GuardrailDisposition.MONITORED)
                self.assertFalse(outcome.halt_pipeline)

    def test_replace_matches(self):
        """Test replace_matches, whose matches may be in any order."""
        matches = [GuardrailMatch(start=4, end=5, text="b"), GuardrailMatch(start=0, end=1, text="a")]
        self.assertEqual(replace_matches("a + b", matches, "_"), "_ + _")
