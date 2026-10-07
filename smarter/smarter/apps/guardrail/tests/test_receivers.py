"""
Test :mod:`smarter.apps.guardrail.receivers` and :mod:`smarter.apps.guardrail.signals`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from unittest import mock

from django.dispatch import Signal

from smarter.apps.guardrail import receivers, signals
from smarter.apps.guardrail.services import GuardrailPipeline

from .base_classes import GuardrailTestBase, input_payload

SIGNALS = ("guardrail_triggered", "guardrail_blocked", "guardrail_escalated", "guardrail_failed")


class TestGuardrailReceivers(GuardrailTestBase):
    """Test the signals and their receivers."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(receivers, "logger")
        self.logger = patcher.start()
        self.addCleanup(patcher.stop)
        self.messages: list[str] = []
        for level in ("info", "warning", "error"):
            getattr(self.logger, level).side_effect = self.log

    def log(self, msg, *args, **kwargs):  # pylint: disable=W0613
        self.messages.append(msg % args if args else msg)

    def test_signals(self):
        """Test that each signal is a Django Signal, with a receiver."""
        for name in SIGNALS + ("guardrail_called",):
            self.assertIsInstance(getattr(signals, name), Signal, name)
        for name in SIGNALS:
            self.assertTrue(getattr(signals, name).has_listeners(), name)

    def test_model_receivers(self):
        """Test that creating and deleting a Guardrail is logged."""
        g = self.create_guardrail("test_receivers_model")
        g.delete()
        logged = "\n".join(self.messages)
        self.assertIn("created", logged)
        self.assertIn("guardrail_deleted", logged)

    def test_pipeline_signals_are_logged(self):
        """Test that a block, and an escalation, are logged, without the text that triggered them."""
        block = self.new_guardrail("test_receivers_block", priority=2, message="Blocked.")
        escalate = self.new_guardrail("test_receivers_escalate", action="escalate", priority=1, severity=5)
        GuardrailPipeline([block, escalate]).run_pre(input_payload("a forbidden secret"))
        logged = "\n".join(self.messages)
        self.assertIn("escalated the input to human review, severity 5", logged)
        self.assertIn("blocked the input: Blocked.", logged)
        self.assertNotIn("a forbidden secret", logged)

    def test_failed_is_logged(self):
        """Test that a failed guardrail is logged."""
        signals.guardrail_failed.send(
            sender=self.__class__,
            guardrail=self.new_guardrail("test_receivers_failed"),
            stage="output",
            error="provider down",
            fail_closed=True,
        )
        self.assertIn("failed on the output, and blocked it: provider down", "\n".join(self.messages))
