"""
The boundary between resolving an LLM tool call and executing it.

See :mod:`smarter.apps.llmtool.runner.models` and :mod:`smarter.apps.llmtool.runner.runner`, and
:doc:`ADR-038 </adr/038-tool-isolation-and-egress>`.
"""

from .models import ToolCall, ToolCallResult
from .runner import (
    TOOL_EXECUTORS,
    InProcessToolRunner,
    ToolExecutor,
    ToolRunner,
    executor_for,
    get_tool_runner,
)

__all__ = [
    "TOOL_EXECUTORS",
    "InProcessToolRunner",
    "ToolCall",
    "ToolCallResult",
    "ToolExecutor",
    "ToolRunner",
    "executor_for",
    "get_tool_runner",
]
