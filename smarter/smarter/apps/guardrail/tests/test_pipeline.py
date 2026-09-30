"""
Test :mod:`smarter.apps.guardrail.services.pipeline` and :mod:`smarter.apps.guardrail.services.engine`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.guardrail.models import GuardrailDisposition
from smarter.apps.guardrail.services import GuardrailPipeline, PipelineDisposition
from smarter.apps.guardrail.services.engine import GuardrailEngine
from smarter.apps.guardrail.services.pipeline import fold
from smarter.apps.guardrail.services.strategies.base import StrategyContext
from smarter.apps.guardrail.signals import (
    guardrail_blocked,
    guardrail_escalated,
    guardrail_failed,
    guardrail_triggered,
)
from smarter.apps.plugin.plugin.tests.base_classes import capture_signal
from smarter.apps.provider.services.text_completion.contracts import GuardrailStage

from .base_classes import (
    FakeGuardrailClient,
    GuardrailTestBase,
    fake_client,
    get_test_data,
    input_payload,
    output_payload,
)

PROMPTS = get_test_data("prompts.yaml")
PII = {"strategy": "detector", "config": {"detectors": ["credit_card", "email"]}, "category": "pii"}


class TestGuardrailPipeline(GuardrailTestBase):
    """Test the guardrail pipeline."""

    def user_text(self, result) -> str:
        """Return the latest user message of a pre stage result."""
        return result.payload["messages"][-1]["content"]

    def test_no_guardrails(self):
        """Test that a pipeline without guardrails allows everything, unchanged."""
        payload = input_payload(PROMPTS["pii"])
        result = GuardrailPipeline([]).run_pre(payload)
        self.assertEqual(result.disposition, PipelineDisposition.ALLOWED)
        self.assertEqual(result.payload, payload)
        self.assertEqual(result.guardrails_evaluated, 0)

    def test_redact(self):
        """Test that a redaction guardrail redacts every match, and records a masked event."""
        g = self.new_guardrail("test_pipeline_redact", action="redact", replacement="[REDACTED {label}]", **PII)
        result = GuardrailPipeline([g], session_key="session").run_pre(input_payload(PROMPTS["pii"]))
        self.assertEqual(result.disposition, PipelineDisposition.REDACTED)
        self.assertEqual(self.user_text(result), PROMPTS["pii_redacted"])
        [event] = self.events(g)
        self.assertEqual(event.disposition, GuardrailDisposition.REDACTED)
        self.assertEqual(event.session_key, "session")
        self.assertNotIn("jane.doe@example.com", event.excerpt)
        self.assertNotIn("4111 1111", event.excerpt)

    def test_input_scans_only_the_user_message(self):
        """Test that the system prompt, which contains 'Ignore', does not trigger an input guardrail."""
        g = self.new_guardrail("test_pipeline_system", config={"keywords": ["ignore"]})
        self.assertFalse(GuardrailPipeline([g]).run_pre(input_payload(PROMPTS["benign"])).blocked)
        self.assertTrue(GuardrailPipeline([g]).run_pre(input_payload("ignore that")).blocked)

    def test_block_halts(self):
        """Test that the first guardrail that blocks stops the pipeline, so later guardrails do not run."""
        block = self.new_guardrail("test_pipeline_block", priority=1, message="Blocked.")
        later = self.new_guardrail("test_pipeline_later", priority=2, action="flag")
        with capture_signal(guardrail_blocked) as blocked:
            result = GuardrailPipeline([later, block]).run_pre(input_payload("a forbidden request"))
        self.assertTrue(result.blocked)
        self.assertEqual(result.fallback_message, "Blocked.")
        self.assertEqual([o.guardrail_name for o in result.outcomes], [block.name])
        self.assertEqual(blocked[0]["message"], "Blocked.")
        self.assertFalse(self.events(later).exists())

    def test_priority_and_sequence(self):
        """Test that guardrails run in priority order, each on the payload as changed by those before it."""
        redact = self.new_guardrail("test_pipeline_first", priority=5, action="redact", **PII)
        # a later keyword guardrail that would block the email address sees it redacted
        email_block = self.new_guardrail("test_pipeline_second", priority=10, config={"keywords": ["jane.doe"]})
        result = GuardrailPipeline([email_block, redact]).run_pre(input_payload(PROMPTS["pii"]))
        self.assertEqual([o.guardrail_name for o in result.outcomes], [redact.name, email_block.name])
        self.assertFalse(result.blocked)
        self.assertEqual(result.disposition, PipelineDisposition.REDACTED)

    def test_disposition_folds(self):
        """Test that the pipeline's disposition is the most severe of its guardrails'."""
        flag = self.new_guardrail("test_pipeline_flag", action="flag", priority=1)
        escalate = self.new_guardrail("test_pipeline_escalate", action="escalate", priority=2)
        with capture_signal(guardrail_escalated) as escalated, capture_signal(guardrail_triggered) as triggered:
            result = GuardrailPipeline([flag, escalate]).run_pre(input_payload("forbidden"))
        self.assertEqual(result.disposition, PipelineDisposition.ESCALATED)
        self.assertEqual(len(triggered), 2)
        self.assertEqual(escalated[0]["event"].disposition, GuardrailDisposition.ESCALATED)
        self.assertEqual(fold(PipelineDisposition.BLOCKED, PipelineDisposition.FLAGGED), PipelineDisposition.BLOCKED)

    def test_monitor_mode(self):
        """Test that a guardrail in monitor mode records what it would have done, and does nothing."""
        g = self.new_guardrail("test_pipeline_monitor", mode="monitor")
        result = GuardrailPipeline([g]).run_pre(input_payload("forbidden"))
        self.assertFalse(result.blocked)
        self.assertEqual(result.disposition, PipelineDisposition.ALLOWED)
        self.assertEqual(self.events(g).get().disposition, GuardrailDisposition.MONITORED)

    def test_inactive_and_other_stage(self):
        """Test that inactive guardrails, and those of the other stage, do not run."""
        inactive = self.new_guardrail("test_pipeline_inactive", is_active=False)
        output = self.new_guardrail("test_pipeline_output", stage="output")
        both = self.new_guardrail("test_pipeline_both", stage="both", action="flag")
        pipeline = GuardrailPipeline([inactive, output, both])
        self.assertEqual(pipeline.guardrails_for(GuardrailStage.PRE), [both])
        self.assertEqual(pipeline.guardrails_for(GuardrailStage.POST), [output, both])
        self.assertEqual(pipeline.run_pre(input_payload("forbidden")).disposition, PipelineDisposition.FLAGGED)

    def test_output(self):
        """Test that output guardrails run on the reply."""
        g = self.new_guardrail("test_pipeline_reply", stage="output", action="redact", **PII)
        result = GuardrailPipeline([g]).run_post(output_payload(PROMPTS["pii"]))
        self.assertEqual(
            result.payload["choices"][0]["message"]["content"], "My card is [REDACTED], and my email is [REDACTED]."
        )
        self.assertEqual(self.events(g).get().stage, "output")

    def test_fail_open(self):
        """Test that a guardrail that fails to run is recorded, and skipped."""
        failing = self.new_guardrail(
            "test_pipeline_fail_open", strategy="llm_judge", config={"judgePrompt": "{text}"}, threshold=0.8
        )
        with fake_client(FakeGuardrailClient(fail=True)), capture_signal(guardrail_failed) as failed:
            result = GuardrailPipeline([failing]).run_pre(input_payload("forbidden"))
        self.assertFalse(result.blocked)
        self.assertIn("failed", result.outcomes[0].error)
        self.assertFalse(failed[0]["fail_closed"])
        self.assertEqual(self.events(failing).get().disposition, GuardrailDisposition.ERROR)

    def test_fail_closed(self):
        """Test that a failClosed guardrail that fails to run blocks, with its message."""
        failing = self.new_guardrail(
            "test_pipeline_fail_closed",
            strategy="llm_judge",
            config={"judgePrompt": "{text}"},
            fail_closed=True,
            message="Try again later.",
        )
        with fake_client(FakeGuardrailClient(fail=True)):
            result = GuardrailPipeline([failing]).run_pre(input_payload(PROMPTS["benign"]))
        self.assertTrue(result.blocked)
        self.assertEqual(result.fallback_message, "Try again later.")
        self.assertEqual(self.events(failing).get().disposition, GuardrailDisposition.BLOCKED)

    def test_scored_strategy(self):
        """Test a scored strategy in the pipeline."""
        judge = self.new_guardrail(
            "test_pipeline_judge",
            strategy="llm_judge",
            config={"judgePrompt": "Judge {text}"},
            threshold=0.8,
            action="flag",
        )
        with fake_client():
            self.assertEqual(
                GuardrailPipeline([judge]).run_pre(input_payload("forbidden")).disposition, PipelineDisposition.FLAGGED
            )
            self.assertEqual(
                GuardrailPipeline([judge]).run_pre(input_payload("fine")).disposition, PipelineDisposition.ALLOWED
            )
        event = self.events(judge).get()
        self.assertEqual(event.excerpt, "forbidden")
        self.assertAlmostEqual(event.confidence, 0.95)

    def test_dry_run(self):
        """Test that a pipeline without record_events records no events."""
        g = self.new_guardrail("test_pipeline_dry_run")
        self.assertTrue(GuardrailPipeline([g], record_events=False).run_pre(input_payload("forbidden")).blocked)
        self.assertFalse(self.events(g).exists())

    def test_engine_catches_unexpected_errors(self):
        """Test that the engine records an unexpected error, rather than raising."""
        g = self.new_guardrail("test_pipeline_bad_config", strategy="regex", pattern="([unclosed")
        outcome = GuardrailEngine().evaluate(
            g, input_payload("x"), GuardrailStage.PRE, StrategyContext(stage=GuardrailStage.PRE)
        )
        self.assertIn("Invalid regex", outcome.error)
        self.assertEqual(outcome.findings, [])
        self.assertGreaterEqual(outcome.duration_ms, 0)
