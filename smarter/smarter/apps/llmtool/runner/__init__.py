"""
The boundary between resolving an LLM tool call and executing it.

See :mod:`smarter.apps.llmtool.runner.models` and :mod:`smarter.apps.llmtool.runner.runner`, and
:doc:`ADR-038 </adr/038-tool-isolation-and-egress>`.
"""

from .models import ToolCall, ToolCallLabel, ToolCallResult
from .runner import (
    TOOL_CALL_MODELS,
    TOOL_EXECUTORS,
    InProcessToolRunner,
    RemoteToolRunner,
    ToolExecutor,
    ToolRunner,
    call_model_for,
    carry_tool_call_label,
    current_tool_call_label,
    executor_for,
    get_tool_runner,
    labeled_tool_calls,
    running_in_tool_worker,
)

__all__ = [
    "TOOL_CALL_MODELS",
    "TOOL_EXECUTORS",
    "InProcessToolRunner",
    "RemoteToolRunner",
    "ToolCall",
    "ToolCallLabel",
    "ToolCallResult",
    "ToolExecutor",
    "ToolRunner",
    "call_model_for",
    "carry_tool_call_label",
    "current_tool_call_label",
    "executor_for",
    "get_tool_runner",
    "labeled_tool_calls",
    "running_in_tool_worker",
]
