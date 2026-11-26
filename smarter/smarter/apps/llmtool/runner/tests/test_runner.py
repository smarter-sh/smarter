"""Test :mod:`smarter.apps.llmtool.runner`: the tool runner, its executors and its models."""

from unittest import mock

from pydantic import ValidationError

from smarter.apps.llmtool.runner import (
    TOOL_EXECUTORS,
    InProcessToolRunner,
    ToolCall,
    ToolCallResult,
    executor_for,
    get_tool_runner,
)
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.unittest.base_classes import SmarterTestBase

EXECUTOR_PATH = "smarter.apps.llmtool.runner.tests.test_runner.echo_executor"


def echo_executor(call: ToolCall) -> ToolCallResult:
    """A test executor: its result is the call's kind."""
    result = ToolCallResult(value=call.kind)
    return result


class TestToolRunner(SmarterTestBase):
    """Test the tool runner."""

    def test_get_tool_runner(self):
        """Test that tool calls run in process."""
        self.assertIsInstance(get_tool_runner(), InProcessToolRunner)

    def test_in_process_runner_runs_the_kinds_executor(self):
        """Test that the in-process runner runs a call with the executor that its kind registered."""
        with mock.patch.dict(TOOL_EXECUTORS, {"echo": EXECUTOR_PATH}):
            result = InProcessToolRunner().run(ToolCall(kind="echo"))
        self.assertEqual(result, ToolCallResult(value="echo"))

    def test_unknown_kind(self):
        """Test that a kind without an executor is a configuration error."""
        with self.assertRaises(SmarterConfigurationError):
            executor_for("no-such-kind")
        with self.assertRaises(SmarterConfigurationError):
            InProcessToolRunner().run(ToolCall(kind="no-such-kind"))

    def test_registered_executors_import(self):
        """Test that every registered executor's dotted path imports, so that a typo fails here and not in a chat."""
        for kind in TOOL_EXECUTORS:
            executor = executor_for(kind)
            self.assertTrue(callable(executor), kind)

    def test_result_outcomes(self):
        """Test the three outcomes of a result, and that a result travels as JSON."""
        succeeded = ToolCallResult(value={"a": [1, 2]})
        self.assertFalse(succeeded.is_error)
        self.assertIsNone(succeeded.failure)
        tool_error = ToolCallResult(value="no such row", is_error=True)
        failed = ToolCallResult(failure="timed out")
        self.assertIsNone(failed.value)
        for result in (succeeded, tool_error, failed):
            self.assertEqual(ToolCallResult.model_validate_json(result.model_dump_json()), result)

    def test_models_are_strict(self):
        """Test that the models refuse unknown fields, and can't be changed after they're made."""
        with self.assertRaises(ValidationError):
            ToolCall(kind="echo", unexpected=1)  # type: ignore[call-arg]
        result = ToolCallResult(value=1)
        with self.assertRaises(ValidationError):
            result.value = 2  # type: ignore[misc]
