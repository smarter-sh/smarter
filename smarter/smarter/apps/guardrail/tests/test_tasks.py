"""
Test :mod:`smarter.apps.guardrail.tasks`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import datetime

from django.utils import timezone

from smarter.apps.guardrail.models import GuardrailEvent
from smarter.apps.guardrail.tasks import EVENT_RETENTION_DAYS, purge_guardrail_events

from .base_classes import GuardrailTestBase


class TestGuardrailTasks(GuardrailTestBase):
    """Test purge_guardrail_events()."""

    def event(self, guardrail, disposition: str, days_old: int, reviewed: bool = False) -> GuardrailEvent:
        e = GuardrailEvent.objects.create(
            guardrail=guardrail,
            guardrail_name=guardrail.name,
            stage="input",
            category="custom",
            strategy="keyword",
            action="block",
            mode="enforce",
            disposition=disposition,
            reviewed=reviewed,
        )
        GuardrailEvent.objects.filter(pk=e.pk).update(created_at=timezone.now() - datetime.timedelta(days=days_old))
        return e

    def test_purge(self):
        """Test that old events are deleted, except those that await review."""
        g = self.new_guardrail("test_tasks_purge")
        old = EVENT_RETENTION_DAYS + 1
        recent = self.event(g, "blocked", 1)
        old_blocked = self.event(g, "blocked", old)
        old_flagged = self.event(g, "flagged", old)
        old_reviewed = self.event(g, "escalated", old, reviewed=True)
        purge_guardrail_events()
        remaining = set(GuardrailEvent.objects.filter(guardrail=g).values_list("pk", flat=True))
        self.assertEqual(remaining, {recent.pk, old_flagged.pk})
        self.assertNotIn(old_blocked.pk, remaining)
        self.assertNotIn(old_reviewed.pk, remaining)

    def test_purge_days(self):
        """Test the days argument."""
        g = self.new_guardrail("test_tasks_days")
        self.event(g, "blocked", 5)
        self.assertGreaterEqual(purge_guardrail_events(days=3), 1)
        self.assertFalse(GuardrailEvent.objects.filter(guardrail=g).exists())
