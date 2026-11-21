"""Test :mod:`smarter.apps.orchestrator.receivers`, the receivers of the orchestrator app's signals."""

import logging
from unittest.mock import MagicMock

from smarter.apps.orchestrator import receivers
from smarter.apps.orchestrator.models import OrchestrationStep
from smarter.apps.orchestrator.signals import (
    orchestration_run_finished,
    orchestration_run_queued,
    orchestration_run_started,
    orchestration_step_finished,
    orchestrator_called,
)
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.log_capture import WrappedLoggerCapture
from smarter.lib.unittest.receivers import ReceiversTestMixin


class TestOrchestratorReceiversArguments(ReceiversTestMixin, SmarterTestBase):
    """Call each receiver of the orchestrator app with mock arguments."""

    receivers_module = receivers


class TestOrchestratorReceivers(SmarterTestBase):
    """Test that each signal of a run's lifecycle is logged once, at its level, without the run's objective."""

    def setUp(self):
        super().setUp()
        self.capture = WrappedLoggerCapture(self, receivers.logger)
        self.orchestrator = MagicMock(pk=7, strategy="sequential", __str__=lambda self: "board-pack")
        self.orchestration_run = MagicMock(
            pk=42,
            orchestrator=self.orchestrator,
            orchestrator_id=7,
            objective="a private objective",
            status="succeeded",
            iteration_count=3,
        )

    def step(self, status: str) -> MagicMock:
        """A recorded step of the run, whose harness's LLMClient is ``writer``."""
        step = MagicMock(sequence=2, status=status, error_message="the provider said something")
        step.harness.llmclient.name = "writer"
        return step

    def test_called(self):
        orchestrator_called.send(sender=self.__class__, orchestrator=self.orchestrator, request=None, data={})
        self.assertIn("called board-pack (id 7)", self.capture.text(logging.DEBUG))

    def test_queued_and_started(self):
        orchestration_run_queued.send(sender=self.__class__, run=self.orchestration_run)
        orchestration_run_started.send(sender=self.__class__, run=self.orchestration_run)
        info = self.capture.text(logging.INFO)
        self.assertIn("queued run 42 of orchestrator 7", info)
        self.assertIn("started run 42 of orchestrator 7, strategy sequential", info)
        self.assertNotIn("a private objective", self.capture.text())

    def test_step_succeeded(self):
        orchestration_step_finished.send(
            sender=self.__class__, run=self.orchestration_run, step=self.step(OrchestrationStep.StepStatus.SUCCEEDED)
        )
        self.assertIn("step 2 of run 42 succeeded, llmclient writer", self.capture.text(logging.INFO))

    def test_step_failed_is_a_warning_without_its_error(self):
        orchestration_step_finished.send(
            sender=self.__class__, run=self.orchestration_run, step=self.step(OrchestrationStep.StepStatus.FAILED)
        )
        self.assertIn("step 2 of run 42 failed, llmclient writer", self.capture.text(logging.WARNING))
        self.assertNotIn("the provider said something", self.capture.text())

    def test_finished(self):
        orchestration_run_finished.send(sender=self.__class__, run=self.orchestration_run)
        self.assertIn("run 42 succeeded after 3 steps", self.capture.text(logging.INFO))
