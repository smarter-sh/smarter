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

    An HTTP tool, e.g. an ApiPlugin's api, also reports the response's ``status_code``, so that the
    app can tell a rejected credential (401, 403) from any other failure.

    :ivar value: The tool's result, as JSON.
    :ivar is_error: Whether the tool answered with an error of its own.
    :ivar failure: Why the call couldn't be made, or None.
    :ivar status_code: The HTTP status of an HTTP tool's response, or None when there was none.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: JsonValue = None
    is_error: bool = False
    failure: Optional[str] = None
    status_code: Optional[int] = None


class ToolCallLabel(BaseModel):
    """
    What a tool call is for, so that the tool worker's log can say so.

    The app sets it around each tool call that the LLM makes
    (:func:`~smarter.apps.llmtool.runner.runner.labeled_tool_calls`), and the remote runner sends it to
    the tool worker beside the call. It holds names and ids only, never a credential, an argument or a
    result: it is logged as is.

    :ivar tool: The tool's name, as users know it, e.g. a plugin's or an MCP tool's name.
    :ivar llmclient: The LLMClient that the call is made for, as ``<name> (<id>)``, or None.
    :ivar session: The chat session's key, masked, or None.
    :ivar request_id: The id of the request that made the call, or None.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: Optional[str] = None
    llmclient: Optional[str] = None
    session: Optional[str] = None
    request_id: Optional[str] = None

    def describe(self) -> str:
        """
        Describe the label for a log line.

        :returns: e.g. ``tool=stackademy_sql llmclient=stackademy (12) session=****a1b2c3 request=r-123``,
            with ``-`` for what isn't known.
        """
        tool = self.tool or "-"
        llmclient = self.llmclient or "-"
        session = self.session or "-"
        request_id = self.request_id or "-"
        description = f"tool={tool} llmclient={llmclient} session={session} request={request_id}"
        return description


__all__ = ["ToolCall", "ToolCallLabel", "ToolCallResult"]
