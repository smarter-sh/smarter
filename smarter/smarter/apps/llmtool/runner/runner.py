"""
The tool runner: where a resolved tool call is executed.

:func:`get_tool_runner` returns the runner that every tool call goes through, as the setting
``app_llmtool_tool_runner`` (``SMARTER_APP_LLMTOOL_TOOL_RUNNER``) chooses:

- :class:`InProcessToolRunner`, the default, executes the call in the app's own process.
- :class:`RemoteToolRunner` sends it, as JSON, to the tool worker, ``smarter-worker-tools``, through the
  Celery queue ``app_tools_tasks_celery_task_queue``, and waits for its result. The worker holds no
  database, no Smarter Secret and no cloud credential: each call brings what it needs (:doc:`ADR-038
  </adr/038-tool-isolation-and-egress>`).

The code that resolves a call is the same either way. Each kind of tool registers its executor in
:data:`TOOL_EXECUTORS`, and its call's model in :data:`TOOL_CALL_MODELS`, by dotted path. A path, rather
than an import, keeps this module free of the apps that it runs tools for, several of which import
from :mod:`smarter.apps.llmtool`.

Inside the tool worker, every call runs in process, whatever the setting says: an executor that uses
the runner itself, e.g. the web search page fetch's robots.txt, must not send its call back to the queue
that it is serving (:func:`running_in_tool_worker`).
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator, Optional, ParamSpec, TypeVar

from django.utils.module_loading import import_string

from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib import logging

from .models import ToolCall, ToolCallLabel, ToolCallResult

# not waffle switched: the tool worker has no database to read a switch from, and some calls run in
# worker threads, where a switch would open a database connection per thread.
logger = logging.getSmarterLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

ToolExecutor = Callable[[ToolCall], ToolCallResult]
"""A function that executes one kind of resolved tool call, and returns its result."""

TOOL_EXECUTORS: dict[str, str] = {
    "api": "smarter.apps.connection.execution.execute_api_call",
    "extension": "smarter.apps.llmtool.extension.execution.execute_extension_call",
    "http": "smarter.apps.llmtool.runner.http.execute_http_call",
    "webfetch": "smarter.apps.llmtool.plugin.websearch_fetch.execute_webfetch_call",
    "mcp": "smarter.apps.mcpclient.execution.execute_mcp_call",
    "sql": "smarter.apps.connection.execution.execute_sql_call",
}
"""Each kind of :class:`~smarter.apps.llmtool.runner.models.ToolCall`, and the dotted path of its executor."""

TOOL_CALL_MODELS: dict[str, str] = {
    "api": "smarter.apps.connection.execution.ApiToolCall",
    "extension": "smarter.apps.llmtool.extension.execution.ExtensionToolCall",
    "http": "smarter.apps.llmtool.runner.http.HttpToolCall",
    "webfetch": "smarter.apps.llmtool.plugin.websearch_fetch.WebFetchToolCall",
    "mcp": "smarter.apps.mcpclient.execution.MCPToolCall",
    "sql": "smarter.apps.connection.execution.SqlToolCall",
}
"""Each kind of tool call, and the dotted path of its model, which rebuilds a call from its JSON in the tool worker."""

DEFAULT_CALL_TIMEOUT_SECONDS = 30.0
"""The timeout of a call that names none of its own."""

REMOTE_TIMEOUT_FACTOR = 4
"""
How many times a call's own timeout the remote runner waits for its result.

A call can make several requests, each with that timeout: an MCP call connects and then calls, a page
fetch reads robots.txt and follows redirects. The executor's own timeouts end the call; this only keeps
the app from waiting for a worker that is gone.
"""

REMOTE_TIMEOUT_MARGIN_SECONDS = 15.0
"""Seconds that the remote runner adds to its wait, for the queue and the worker's start."""

MAX_REMOTE_TIMEOUT_SECONDS = 600.0
"""The longest that the remote runner waits for a result."""

_in_tool_worker: ContextVar[bool] = ContextVar("in_tool_worker", default=False)
_tool_call_label: ContextVar[Optional[ToolCallLabel]] = ContextVar("smarter_tool_call_label", default=None)


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


def call_model_for(kind: str) -> type[ToolCall]:
    """
    Return the model of a kind of tool call.

    :param kind: The call's ``kind``.
    :returns: The model, a subclass of :class:`~smarter.apps.llmtool.runner.models.ToolCall`.
    :raises SmarterConfigurationError: If no model is registered for the kind.
    """
    path = TOOL_CALL_MODELS.get(kind)
    if path is None:
        raise SmarterConfigurationError(f"no tool call model is registered for the kind {kind!r}.")
    model: type[ToolCall] = import_string(path)
    return model


@contextmanager
def running_in_tool_worker() -> Iterator[None]:
    """
    Mark the code inside the ``with`` block as running in the tool worker, so that :func:`get_tool_runner` runs its calls in process.

    The tool worker's task, :func:`smarter.apps.llmtool.tasks.run_tool_call`, runs each call inside it.
    """
    token = _in_tool_worker.set(True)
    try:
        yield
    finally:
        _in_tool_worker.reset(token)


@contextmanager
def labeled_tool_calls(label: ToolCallLabel) -> Iterator[None]:
    """
    Label every tool call made inside the ``with`` block, so that the tool worker's log says what it was for.

    The chat provider sets it around each tool call that the LLM makes
    (``OpenAICompatibleChatProvider.process_tool_call()``). A call made without one is logged without it.

    :param label: The label, names and ids only.
    """
    token = _tool_call_label.set(label)
    try:
        yield
    finally:
        _tool_call_label.reset(token)


def current_tool_call_label() -> Optional[ToolCallLabel]:
    """
    Return the label that :func:`labeled_tool_calls` set, if any.

    :returns: The label, or None.
    """
    label = _tool_call_label.get()
    return label


def carry_tool_call_label(function: Callable[P, R]) -> Callable[P, R]:
    """
    Return a function that runs ``function`` with the current tool call label.

    A thread doesn't inherit the context variables of the code that starts it, so a call made from a
    thread pool, e.g. an ImageSearchPlugin's validation of image urls, would lose its label.

    :param function: The function that a thread runs.
    :returns: The function, wrapped.
    """
    label = current_tool_call_label()

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if label is None:
            return function(*args, **kwargs)
        with labeled_tool_calls(label):
            return function(*args, **kwargs)

    return wrapper


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


def call_timeout(call: ToolCall) -> float:
    """
    Return the timeout that a call names, its own or its MCP endpoint's.

    :param call: The call.
    :returns: Seconds, or :data:`DEFAULT_CALL_TIMEOUT_SECONDS` if it names none.
    """
    timeout = getattr(call, "timeout", None)
    if timeout is None:
        endpoint = getattr(call, "endpoint", None)
        timeout = getattr(endpoint, "timeout", None)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        return DEFAULT_CALL_TIMEOUT_SECONDS
    return float(timeout)


def remote_timeout(call: ToolCall) -> float:
    """
    Return how long the remote runner waits for a call's result.

    :param call: The call.
    :returns: Seconds: the call's timeout times :data:`REMOTE_TIMEOUT_FACTOR`, plus
        :data:`REMOTE_TIMEOUT_MARGIN_SECONDS`, at most :data:`MAX_REMOTE_TIMEOUT_SECONDS`.
    """
    seconds = call_timeout(call) * REMOTE_TIMEOUT_FACTOR + REMOTE_TIMEOUT_MARGIN_SECONDS
    return min(seconds, MAX_REMOTE_TIMEOUT_SECONDS)


def describe_remote_failure(error: Exception, timeout: float) -> str:
    """
    Describe, for the LLM, why the tool worker didn't return a call's result.

    :param error: What the wait raised.
    :param timeout: Seconds that the runner waited.
    :returns: The description.
    """
    # pylint: disable=import-outside-toplevel
    from celery.exceptions import TimeoutError as CeleryTimeoutError

    if isinstance(error, CeleryTimeoutError):
        return f"the tool worker did not answer within {timeout:g} seconds."
    return f"the tool worker could not run the tool: {type(error).__name__}: {error}"


class RemoteToolRunner(ToolRunner):
    """
    Sends each call to the tool worker, ``smarter-worker-tools``, and waits for its result.

    The call travels as JSON, in a Celery task on the queue ``app_tools_tasks_celery_task_queue``, and
    its result comes back through the result backend, the broker's Redis. A worker that doesn't answer
    in time, or a task that fails, is a result with a ``failure``, as any call that couldn't be made is.

    .. warning::

        The task's arguments hold the call's credentials, in Redis, until the worker takes the task.
        Smarter's Celery app sends messages with protocol 1, which has no ``argsrepr`` header, and its
        worker logs a task's name and id, not its arguments. The tool worker runs without task events
        (``-E``), so that they don't reach an events stream either.
    """

    def run(self, call: ToolCall) -> ToolCallResult:
        """
        Execute a resolved tool call in the tool worker.

        :param call: The call.
        :returns: The worker's result, or a result with a ``failure`` if the worker doesn't answer in
            time, or the task fails.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmtool.tasks import run_tool_call

        timeout = remote_timeout(call)
        label = current_tool_call_label()
        label_json = label.model_dump_json() if label is not None else None
        async_result = run_tool_call.apply_async(
            args=(call.kind, call.model_dump_json(), label_json),
            queue=smarter_settings.app_tools_tasks_celery_task_queue,
            expires=timeout,
        )
        try:
            # the app's request, not a task, usually waits here. A task that makes a tool call, e.g. an
            # orchestration, waits too: the tool worker is another worker, so it can't deadlock.
            payload = async_result.get(timeout=timeout, disable_sync_subtasks=False)
        # a remote call can fail in any way: the queue, the worker, the result backend.
        # pylint: disable=broad-exception-caught
        except Exception as e:
            failure = describe_remote_failure(e, timeout)
            # the exception's type only: its message can hold a url with a credential.
            description = label.describe() if label is not None else "unlabeled"
            logger.warning(
                "the tool worker did not return the %s call %s: %s (%s)",
                call.kind,
                async_result.id,
                type(e).__name__,
                description,
            )
            return ToolCallResult(failure=failure)
        finally:
            async_result.forget()
        result = ToolCallResult.model_validate_json(payload)
        return result


def get_tool_runner() -> ToolRunner:
    """
    Return the runner that tool calls go through.

    :returns: :class:`RemoteToolRunner` when ``app_llmtool_tool_runner`` is ``remote``, outside the tool
        worker; otherwise :class:`InProcessToolRunner`.
    """
    if _in_tool_worker.get():
        return InProcessToolRunner()
    if smarter_settings.app_llmtool_tool_runner == "remote":
        return RemoteToolRunner()
    return InProcessToolRunner()


__all__ = [
    "MAX_REMOTE_TIMEOUT_SECONDS",
    "TOOL_CALL_MODELS",
    "TOOL_EXECUTORS",
    "InProcessToolRunner",
    "RemoteToolRunner",
    "ToolExecutor",
    "ToolRunner",
    "call_model_for",
    "call_timeout",
    "carry_tool_call_label",
    "current_tool_call_label",
    "describe_remote_failure",
    "executor_for",
    "get_tool_runner",
    "labeled_tool_calls",
    "remote_timeout",
    "running_in_tool_worker",
]
