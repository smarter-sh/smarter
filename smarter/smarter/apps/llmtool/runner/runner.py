"""
The tool runner: where a resolved tool call is executed.

:func:`get_tool_runner` returns the runner that every tool call goes through. Today that is the
:class:`InProcessToolRunner`, which executes the call in the app's own process, as before. The
boundary exists so that a remote runner can send the same call to a worker that holds no
credentials, without the code that resolves a call changing (:doc:`ADR-038
</adr/038-tool-isolation-and-egress>`, phase 2).

Each kind of tool registers its executor in :data:`TOOL_EXECUTORS`, by dotted path. A path,
rather than an import, keeps this module free of the apps that it runs tools for, several of
which import from :mod:`smarter.apps.llmtool`.
"""

from abc import ABC, abstractmethod
from typing import Callable

from django.utils.module_loading import import_string

from smarter.common.exceptions import SmarterConfigurationError

from .models import ToolCall, ToolCallResult

ToolExecutor = Callable[[ToolCall], ToolCallResult]
"""A function that executes one kind of resolved tool call, and returns its result."""

TOOL_EXECUTORS: dict[str, str] = {
    "api": "smarter.apps.connection.execution.execute_api_call",
    "http": "smarter.apps.llmtool.runner.http.execute_http_call",
    "webfetch": "smarter.apps.llmtool.plugin.websearch_fetch.execute_webfetch_call",
    "mcp": "smarter.apps.mcpclient.execution.execute_mcp_call",
    "sql": "smarter.apps.connection.execution.execute_sql_call",
}
"""Each kind of :class:`~smarter.apps.llmtool.runner.models.ToolCall`, and the dotted path of its executor."""


def executor_for(kind: str) -> ToolExecutor:
    """
    Return the executor of a kind of tool call.

    :param kind: The call's ``kind``.
    :returns: The executor.
    :raises SmarterConfigurationError: If no executor is registered for the kind.
    """
    path = TOOL_EXECUTORS.get(kind)
    if path is None:
        raise SmarterConfigurationError(f"no tool executor is registered for the kind {kind!r}.")
    executor: ToolExecutor = import_string(path)
    return executor


class ToolRunner(ABC):
    """Executes resolved tool calls."""

    @abstractmethod
    def run(self, call: ToolCall) -> ToolCallResult:
        """
        Execute a resolved tool call.

        :param call: The call, with everything it needs already resolved.
        :returns: The result. A call that couldn't be made is a result with a ``failure``,
            not an exception.
        """


class InProcessToolRunner(ToolRunner):
    """Executes each call in this process, with the executor that its kind registered."""

    def run(self, call: ToolCall) -> ToolCallResult:
        """
        Execute a resolved tool call in this process.

        :param call: The call.
        :returns: The executor's result.
        :raises SmarterConfigurationError: If no executor is registered for the call's kind.
        """
        # no logging here: some calls run in worker threads, where the waffle switched logger
        # would open a database connection per thread to read its switch.
        executor = executor_for(call.kind)
        result = executor(call)
        return result


def get_tool_runner() -> ToolRunner:
    """
    Return the runner that tool calls go through.

    :returns: The in-process runner. A setting will choose a remote runner here (ADR-038, phase 2).
    """
    runner = InProcessToolRunner()
    return runner


__all__ = [
    "TOOL_EXECUTORS",
    "InProcessToolRunner",
    "ToolExecutor",
    "ToolRunner",
    "executor_for",
    "get_tool_runner",
]
