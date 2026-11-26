"""
The call and result models of :mod:`smarter.apps.llmtool.runner`.

A tool call is resolved in the app, where the database and the Smarter Secrets are, into a
:class:`ToolCall`: plain values, with every credential the call needs already decrypted, and
nothing that needs a database connection. A :class:`~smarter.apps.llmtool.runner.runner.ToolRunner`
executes it and returns a :class:`ToolCallResult`. Both are Pydantic models, so that a call can
be sent to, and its result returned from, a worker that holds no credentials of its own (see
:doc:`ADR-038 </adr/038-tool-isolation-and-egress>`).

.. warning::

    A resolved call holds credentials. Never log it, or its ``model_dump()``. Fields that hold
    credentials are excluded from ``repr()``, as a guard against an accidental log line.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, JsonValue


class ToolCall(BaseModel):
    """
    A tool call, resolved for execution.

    Each kind of tool subclasses it, with a ``kind`` of its own, and registers the function that
    executes it in :data:`smarter.apps.llmtool.runner.runner.TOOL_EXECUTORS`.

    :ivar kind: The kind of tool, e.g. ``mcp``. It selects the executor.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str


class ToolCallResult(BaseModel):
    """
    The result of a tool call.

    A call has one of three outcomes:

    - it succeeded: ``value`` is its result, and ``is_error`` is False;
    - the tool answered with an error of its own, e.g. an MCP tool's ``isError``: ``value``
      describes it, and ``is_error`` is True;
    - it couldn't be made: refused, unreachable, timed out or misconfigured. ``failure``
      describes why, and ``value`` is None.

    :ivar value: The tool's result, as JSON.
    :ivar is_error: Whether the tool answered with an error of its own.
    :ivar failure: Why the call couldn't be made, or None.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: JsonValue = None
    is_error: bool = False
    failure: Optional[str] = None


__all__ = ["ToolCall", "ToolCallResult"]
