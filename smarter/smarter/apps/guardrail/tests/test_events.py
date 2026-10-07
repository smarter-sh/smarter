"""
Test :mod:`smarter.apps.guardrail.services.events`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from unittest import mock

from smarter.apps.guardrail.models import GuardrailDisposition, GuardrailEvent
from smarter.apps.guardrail.services.events import (
    excerpt,
    mask,
    record_event,
    stage_name,
)
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailFinding,
    GuardrailMatch,
    GuardrailStage,
)

from .base_classes import GuardrailTestBase


def finding(category: str, matches=None) -> GuardrailFinding:
    """Return a triggered finding."""
    return GuardrailFinding(
        guardrail_id=1,
        guardrail_name="test",
        category=category,
        strategy="detector",
        action="redact",
        severity=4,
        triggered=True,
        confidence=1.0,
        matches=matches or [],
        rationale="why",
    )


CARD = GuardrailMatch(start=0, end=19, text="4111 1111 1111 1111", label="credit_card")
KEY = GuardrailMatch(start=0, end=20, text="AKIAIOSFODNN7EXAMPLE", label="aws_access_key")


class TestGuardrailEvents(GuardrailTestBase):
    """Test the masking of excerpts, and the recording of events."""

    def test_mask(self):
        """Test that personal data keeps its last four characters, secrets only their length, and the rest all."""
        self.assertEqual(mask("4111 1111 1111 1111", "pii"), "*" * 15 + "1111")
        self.assertEqual(mask("short", "pii"), "****")
        self.assertEqual(mask("AKIAIOSFODNN7EXAMPLE", "secrets"), "[20 characters]")
        self.assertEqual(mask("drop table", "prompt_injection"), "drop table")

    def test_excerpt(self):
        """Test that excerpts are masked for the pii and secrets categories."""
        self.assertEqual(excerpt(finding("pii", [CARD]), None), "credit_card: " + "*" * 15 + "1111")
        self.assertEqual(excerpt(finding("secrets", [KEY]), None), "aws_access_key: [20 characters]")
        # scored strategies have no matches: the segment is the excerpt, unless it may contain pii
        self.assertEqual(excerpt(finding("toxicity"), "a rude message"), "a rude message")
        self.assertEqual(excerpt(finding("pii"), "a message"), "[9 characters]")
        self.assertIsNone(excerpt(finding("toxicity"), None))

    def test_record_event(self):
        """Test that record_event records a masked event."""
        guardrail = self.new_guardrail("test_events_record", category="pii")
        event = record_event(
            guardrail=guardrail,
            stage=GuardrailStage.PRE,
            disposition=GuardrailDisposition.REDACTED,
            finding=finding("pii", [CARD]),
            session_key="abc",
        )
        self.assertIsInstance(event, GuardrailEvent)
        self.assertEqual(event.guardrail_name, guardrail.name)
        self.assertEqual(event.stage, "input")
        self.assertEqual(event.session_key, "abc")
        self.assertNotIn("4111 1111", event.excerpt)
        self.assertFalse(event.reviewed)
        self.assertEqual(str(event), f"{guardrail.name} input redacted")

    def test_record_event_failure(self):
        """Test that a failure to record an event is logged, and does not raise."""
        guardrail = self.new_guardrail("test_events_failure")
        with mock.patch.object(GuardrailEvent.objects, "create", side_effect=RuntimeError("database down")):
            self.assertIsNone(record_event(guardrail=guardrail, stage=GuardrailStage.POST, disposition="error"))

    def test_stage_name(self):
        """Test stage_name."""
        self.assertEqual(stage_name(GuardrailStage.PRE), "input")
        self.assertEqual(stage_name(GuardrailStage.POST), "output")

    def test_deleted_guardrail_keeps_events(self):
        """Test that deleting a guardrail keeps its events, with its name."""
        guardrail = self.create_guardrail("test_events_deleted")
        event = record_event(guardrail=guardrail, stage=GuardrailStage.PRE, disposition="blocked")
        self.addCleanup(GuardrailEvent.objects.filter(pk=event.pk).delete)
        guardrail.delete()
        event.refresh_from_db()
        self.assertIsNone(event.guardrail)
        self.assertEqual(event.guardrail_name, "test_events_deleted")
