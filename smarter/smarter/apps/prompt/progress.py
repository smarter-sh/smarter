"""
Interim progress of a prompt, for clients that stream the prompt api's response.

A prompt can take a while: the LLM may call tools, plugins and MCP servers, and each tool call
adds another round trip to the LLM. A client that sends ``Accept: text/event-stream`` to a
LLMClient's prompt api receives Server-Sent Events (SSE) while the prompt runs, followed by the
same JSON that a non-streaming client receives. See
:class:`smarter.apps.llmclient.api.v1.views.base.LLMClientApiBaseViewSet`.

The prompt itself runs synchronously, in a worker thread, exactly as it does for a non-streaming
client. Its progress comes from the signals that the prompt already sends (``chat_request``,
``llm_tool_requested``, ``chat_plugin_called``, ``mcpclient_tool_called``, ...). The receivers in
this module forward them to the sink of the prompt that sent them, which is held in a
:class:`contextvars.ContextVar`, so that concurrent prompts never see each other's events.

SSE payload format
------------------

- ``retry: 3000`` is sent once, first.
- ``event: progress`` with ``data: {"type": ..., "message": ..., ...}`` for each step.
- ``: keepalive`` comments while the prompt is idle, e.g. waiting on the LLM.
- ``event: result`` with ``data: {"status": <http status>, "response": <the api's json>}``, last.
"""

import asyncio
import contextvars
import json
from contextlib import contextmanager
from http import HTTPStatus
from typing import Any, AsyncIterator, Callable, Generator, Optional

from asgiref.sync import sync_to_async
from django.db import close_old_connections
from django.dispatch import receiver
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse

from smarter.apps.mcpclient.signals import (
    mcpclient_tool_called,
    mcpclient_tool_failed,
    mcpclient_tool_responded,
)
from smarter.lib import logging

from .signals import (
    chat_plugin_called,
    chat_request,
    llm_tool_requested,
    llm_tool_responded,
)

logger = logging.getLogger(__name__)

EVENT_STREAM_CONTENT_TYPE = "text/event-stream"
KEEPALIVE_SECONDS = 15.0
MAX_ARGUMENTS_LENGTH = 500

ProgressSink = Callable[[dict[str, Any]], None]
_progress_sink: contextvars.ContextVar[Optional[ProgressSink]] = contextvars.ContextVar(
    "smarter_prompt_progress_sink", default=None
)


class PromptProgressEvents:
    """The ``type`` of each progress event."""

    LLM_REQUEST = "llm_request"
    TOOL_REQUESTED = "tool_requested"
    TOOL_RESPONDED = "tool_responded"
    PLUGIN_CALLED = "plugin_called"
    MCP_TOOL_CALLED = "mcp_tool_called"
    MCP_TOOL_RESPONDED = "mcp_tool_responded"
    MCP_TOOL_FAILED = "mcp_tool_failed"


@contextmanager
def progress_sink(sink: ProgressSink) -> Generator[None, None, None]:
    """
    Send the progress events of the prompt that runs in this context to ``sink``.

    :param sink: Called with each progress event, a JSON-serializable dict.
    :type sink: ProgressSink
    """
    token = _progress_sink.set(sink)
    try:
        yield
    finally:
        _progress_sink.reset(token)


def emit(event_type: str, message: str, **detail: Any) -> None:
    """
    Send a progress event to the current prompt's sink, if it has one.

    A prompt without a streaming client has no sink, so this does nothing. A failing sink is
    logged, and never fails the prompt.

    :param event_type: One of :class:`PromptProgressEvents`.
    :type event_type: str
    :param message: A short, human-readable description of the step.
    :type message: str
    :param detail: Other JSON-serializable fields of the event.
    """
    sink = _progress_sink.get()
    if sink is None:
        return
    try:
        sink({"type": event_type, "message": message, **detail})
    # pylint: disable=broad-exception-caught
    except Exception:
        logger.exception("%s.emit() failed to send a progress event.", __name__)


def wants_event_stream(request: HttpRequest) -> bool:
    """
    True if the client asked for the prompt api's response as Server-Sent Events.

    :param request: The prompt api's request.
    :type request: django.http.HttpRequest
    :returns: True if the request's Accept header includes ``text/event-stream``.
    :rtype: bool
    """
    return EVENT_STREAM_CONTENT_TYPE in request.META.get("HTTP_ACCEPT", "")


def _arguments_text(arguments: Any) -> str:
    """A tool call's arguments, as text, truncated for display."""
    text = arguments if isinstance(arguments, str) else json.dumps(arguments, default=str)
    return text if len(text) <= MAX_ARGUMENTS_LENGTH else text[:MAX_ARGUMENTS_LENGTH] + "..."


def _tool_name(tool_call: Any) -> str:
    """The function name of a serialized tool call."""
    function = tool_call.get("function") if isinstance(tool_call, dict) else None
    return str(function.get("name", "")) if isinstance(function, dict) else ""


def _is_tool_call_loop(sender: Any) -> bool:
    """
    True for the signals that the provider's tool call loop sends.

    The built-in functions (e.g. the calculator) send ``llm_tool_requested`` and
    ``llm_tool_responded`` themselves too, which would duplicate the loop's events.
    """
    return getattr(sender, "__name__", "") == "process_tool_call"


def _sse(event: Optional[str], data: Any) -> str:
    """One SSE frame.

    Its JSON data has no newlines, so it fits on one ``data:`` line.
    """
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(data, default=str)}\n\n"


# ------------------------------------------------------------------------------
# signal receivers
# ------------------------------------------------------------------------------


@receiver(chat_request, dispatch_uid="smarter.apps.prompt.progress.chat_request")
def handle_chat_request(sender, iteration: Optional[int] = None, **kwargs):
    """A request to the LLM: the prompt itself, or the results of its tool calls."""
    if iteration and iteration > 1:
        emit(PromptProgressEvents.LLM_REQUEST, "Sending the tool results to the LLM", iteration=iteration)
    else:
        emit(PromptProgressEvents.LLM_REQUEST, "Sending the prompt to the LLM", iteration=iteration or 1)


@receiver(llm_tool_requested, dispatch_uid="smarter.apps.prompt.progress.llm_tool_requested")
def handle_llm_tool_requested(sender, tool_call: Optional[dict] = None, **kwargs):
    """The LLM called a tool."""
    if not _is_tool_call_loop(sender):
        return
    name = _tool_name(tool_call)
    arguments = (tool_call or {}).get("function", {}).get("arguments", "")
    emit(
        PromptProgressEvents.TOOL_REQUESTED,
        f"Calling tool {name}",
        tool=name,
        arguments=_arguments_text(arguments),
    )


@receiver(llm_tool_responded, dispatch_uid="smarter.apps.prompt.progress.llm_tool_responded")
def handle_llm_tool_responded(sender, tool_call: Optional[dict] = None, **kwargs):
    """A tool returned its result to the LLM."""
    if not _is_tool_call_loop(sender):
        return
    name = _tool_name(tool_call)
    emit(PromptProgressEvents.TOOL_RESPONDED, f"Tool {name} responded", tool=name)


@receiver(chat_plugin_called, dispatch_uid="smarter.apps.prompt.progress.chat_plugin_called")
def handle_chat_plugin_called(sender, plugin: Any = None, **kwargs):
    """The LLM called a plugin."""
    name = str(getattr(plugin, "name", "") or "")
    emit(PromptProgressEvents.PLUGIN_CALLED, f"Running plugin {name}", plugin=name)


@receiver(mcpclient_tool_called, dispatch_uid="smarter.apps.prompt.progress.mcpclient_tool_called")
def handle_mcpclient_tool_called(sender, mcpclient: Any = None, tool_name: str = "", arguments: Any = None, **kwargs):
    """The LLM called an MCP server's tool."""
    server = str(getattr(mcpclient, "name", "") or "")
    emit(
        PromptProgressEvents.MCP_TOOL_CALLED,
        f"Calling MCP server {server}: {tool_name}",
        mcpclient=server,
        tool=tool_name,
        arguments=_arguments_text(arguments or {}),
    )


@receiver(mcpclient_tool_responded, dispatch_uid="smarter.apps.prompt.progress.mcpclient_tool_responded")
def handle_mcpclient_tool_responded(sender, mcpclient: Any = None, tool_name: str = "", **kwargs):
    """An MCP server's tool returned a result."""
    server = str(getattr(mcpclient, "name", "") or "")
    emit(
        PromptProgressEvents.MCP_TOOL_RESPONDED,
        f"MCP server {server} responded: {tool_name}",
        mcpclient=server,
        tool=tool_name,
        is_error=bool(kwargs.get("is_error", False)),
    )


@receiver(mcpclient_tool_failed, dispatch_uid="smarter.apps.prompt.progress.mcpclient_tool_failed")
def handle_mcpclient_tool_failed(sender, mcpclient: Any = None, tool_name: str = "", error: str = "", **kwargs):
    """An MCP server's tool could not be called."""
    server = str(getattr(mcpclient, "name", "") or "")
    emit(
        PromptProgressEvents.MCP_TOOL_FAILED,
        f"MCP server {server} failed: {tool_name}",
        mcpclient=server,
        tool=tool_name,
        error=error,
    )


# ------------------------------------------------------------------------------
# the streaming response
# ------------------------------------------------------------------------------


def _response_json(response: HttpResponse) -> Any:
    """The JSON content of the prompt api's response, or its text if it isn't JSON."""
    content = response.content.decode(response.charset or "utf-8")
    try:
        return json.loads(content)
    except ValueError:
        return {"error": content}


async def prompt_event_stream(
    complete: Callable[[], HttpResponse], on_error: Callable[[Exception], HttpResponse]
) -> AsyncIterator[str]:
    """
    Run a prompt in a worker thread, and yield its progress, then its result, as SSE frames.

    :param complete: Runs the prompt synchronously, and returns the prompt api's JSON response.
    :type complete: Callable[[], django.http.HttpResponse]
    :param on_error: Returns the prompt api's JSON error response for an exception that
        ``complete`` raised.
    :type on_error: Callable[[Exception], django.http.HttpResponse]
    :yields: SSE frames: progress events and keepalives, then the result.
    :rtype: AsyncIterator[str]
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    def sink(event: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def run() -> HttpResponse:
        try:
            with progress_sink(sink):
                try:
                    return complete()
                # pylint: disable=broad-exception-caught
                except Exception as e:
                    logger.exception("%s.prompt_event_stream() the prompt failed.", __name__)
                    return on_error(e)
        finally:
            # the worker thread's database connection is its own.
            close_old_connections()

    yield "retry: 3000\n\n"
    task = asyncio.ensure_future(sync_to_async(run, thread_sensitive=False)())
    try:
        while not task.done() or not queue.empty():
            getter = asyncio.ensure_future(queue.get())
            done, _ = await asyncio.wait({getter, task}, timeout=KEEPALIVE_SECONDS, return_when=asyncio.FIRST_COMPLETED)
            if getter in done:
                yield _sse("progress", getter.result())
                continue
            getter.cancel()
            if not done:
                yield ": keepalive\n\n"
        response = task.result()
        yield _sse("result", {"status": response.status_code, "response": _response_json(response)})
    finally:
        # a client that disconnects doesn't stop the prompt, which finishes in its thread,
        # and is saved in the chat session's history.
        if not task.done():
            logger.info("%s.prompt_event_stream() the client disconnected before the prompt finished.", __name__)


def prompt_event_stream_response(
    complete: Callable[[], HttpResponse], on_error: Callable[[Exception], HttpResponse]
) -> StreamingHttpResponse:
    """
    The prompt api's response as Server-Sent Events.

    See :func:`prompt_event_stream`.

    :param complete: Runs the prompt synchronously, and returns the prompt api's JSON response.
    :type complete: Callable[[], django.http.HttpResponse]
    :param on_error: Returns the prompt api's JSON error response for an exception that
        ``complete`` raised.
    :type on_error: Callable[[Exception], django.http.HttpResponse]
    :returns: A streaming ``text/event-stream`` response, whose http status is always 200. The
        prompt's own status is in its ``result`` event.
    :rtype: django.http.StreamingHttpResponse
    """
    response = StreamingHttpResponse(
        prompt_event_stream(complete, on_error),
        content_type=EVENT_STREAM_CONTENT_TYPE,
        status=HTTPStatus.OK.value,
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


__all__ = [
    "PromptProgressEvents",
    "emit",
    "progress_sink",
    "prompt_event_stream",
    "prompt_event_stream_response",
    "wants_event_stream",
]
