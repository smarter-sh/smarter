"""
The one cache of tool call results.

An LLM's tool call is answered by an MCP server, an Extension or the Smarter Project MCP
server, and each caches the results it can with :func:`cached_tool_call`, so that the same
call, from any LLMClient or conversation, is answered without running the tool again. The
rules live here, once:

- The key is the caller's ``namespace``, its ``key`` (plain values that identify the tool and
  everything else that can change its result), and the call's arguments, as canonical JSON.
- A result is JSON (:data:`ToolCall`), so that it can be stored, and shared by every caller.
- An error is never stored, whether the call raises it or returns it. A returned error is
  recognized by the call's ``is_error`` check, :func:`is_error_result` by default.
- A ``timeout`` of 0 or less runs the call without the cache.
- The result says whether it came from the cache, for the caller's signals and logs.

Each caller decides what may be cached at all: a tool that may change something, or whose
result depends on who calls it, is called with a timeout of 0.

**Example usage**::

    result = cached_tool_call(
        "mcpclient", (mcpclient.pk, mcpclient.fingerprint, "tool", "search"), {"query": "dns"}, 3600, run
    )
    result.value, result.cached
"""

from dataclasses import dataclass
from typing import Callable, Union

from cache_results import cache_results
from pydantic import BaseModel, JsonValue

from smarter.lib import json

ERROR_TEXT_PREFIX = "Error:"
"""How a tool's result that is text begins when it is an error, e.g. an MCP tool's."""

ERROR_KEY = "error"
"""The key of a tool's result that is a JSON object when it is an error, e.g. an Extension tool's or a budget refusal."""

ToolCall = Callable[[], JsonValue]
"""
A tool call, ready to run: it takes no arguments, and returns the tool's result as JSON.

It reports an error by raising, or by returning a result that its ``is_error`` check
recognizes. Either way, the error is returned to the LLM and never cached.
"""

ToolCallErrorCheck = Callable[[JsonValue], bool]
"""Whether a tool's result is an error.

See :func:`is_error_result`.
"""

ToolCallKeyPart = Union[str, int, float, bool, None]
"""A plain value that identifies a tool call, e.g. an id, a version or a tool's name."""


@dataclass(frozen=True)
class CachedToolResult:
    """
    The result of a tool call.

    :param value: The tool's result.
    :param cached: True if the result came from the cache, without running the tool.
    """

    value: JsonValue
    cached: bool


class _ErrorResult(Exception):
    """Raised inside the cached function for a result that is an error, so that it is not stored."""

    def __init__(self, value: JsonValue):
        super().__init__("the tool returned an error")
        self.value = value


def is_error_result(value: JsonValue) -> bool:
    """
    Return whether a tool's result is an error, by the conventions that Smarter's tools follow.

    :param value: The tool's result.
    :returns: True for text that begins with :data:`ERROR_TEXT_PREFIX`, a JSON object with an
        :data:`ERROR_KEY`, or that object serialized as text.
    """
    if isinstance(value, dict):
        return ERROR_KEY in value
    if isinstance(value, str):
        text = value.lstrip()
        if text.startswith(ERROR_TEXT_PREFIX):
            return True
        if text.startswith("{") and f'"{ERROR_KEY}"' in text:
            try:
                parsed = json.loads(text)
            except ValueError:
                return False
            return isinstance(parsed, dict) and ERROR_KEY in parsed
    return False


def canonical_arguments(arguments: Union[BaseModel, JsonValue]) -> str:
    """
    Return a tool call's arguments in the form that is part of its cache key.

    :param arguments: Validated arguments, as a Pydantic model, or the LLM's JSON arguments.
    :returns: A model's JSON, in the order of its fields, or the JSON with its keys sorted.
    """
    if isinstance(arguments, BaseModel):
        return arguments.model_dump_json()
    return json.dumps(arguments, sort_keys=True, default=str)


def cached_tool_call(
    namespace: str,
    key: tuple[ToolCallKeyPart, ...],
    arguments: Union[BaseModel, JsonValue],
    timeout: int,
    call: ToolCall,
    is_error: ToolCallErrorCheck = is_error_result,
) -> CachedToolResult:
    """
    Return a tool call's result, cached for ``timeout`` seconds, unless it is an error.

    :param namespace: The kind of tool, e.g. ``mcpclient``, so that two kinds never share a key.
    :param key: Plain values that identify the tool, and everything else that can change its
        result, e.g. an MCPClient's id and fingerprint, and the tool's name.
    :param arguments: The call's arguments.
    :param timeout: Seconds to cache the result. 0 or less runs the call without the cache.
    :param call: Runs the tool, and returns its result. See :data:`ToolCall`.
    :param is_error: Whether a result is an error, which is returned but not cached.
    :returns: The result, and whether it came from the cache.
    :raises Exception: Whatever ``call`` raises, which is not cached either.
    """
    if timeout <= 0:
        return CachedToolResult(value=call(), cached=False)
    executed = False

    # pylint: disable=W0613
    @cache_results(timeout=timeout)
    def get_cached_tool_call_result(namespace: str, key: tuple, arguments: str) -> JsonValue:
        nonlocal executed
        executed = True
        value = call()
        if is_error(value):
            # raised, rather than returned, so that @cache_results stores nothing.
            raise _ErrorResult(value)
        return value

    try:
        value = get_cached_tool_call_result(namespace, key, canonical_arguments(arguments))
    except _ErrorResult as error:
        return CachedToolResult(value=error.value, cached=False)
    return CachedToolResult(value=value, cached=not executed)


__all__ = [
    "ERROR_KEY",
    "ERROR_TEXT_PREFIX",
    "CachedToolResult",
    "ToolCall",
    "ToolCallErrorCheck",
    "ToolCallKeyPart",
    "cached_tool_call",
    "canonical_arguments",
    "is_error_result",
]
