"""
The execution of an Extension's tool call, from its resolved :class:`ExtensionToolCall`.

:class:`~smarter.apps.llmtool.extension.toolkit.ExtensionToolkit` resolves each call in the app: it
validates the LLM's arguments, reads the extension's settings, decrypting its secrets, and its waffle
switches, and names the caller by plain identifiers. The tool runner (:mod:`smarter.apps.llmtool.runner`)
executes it with :func:`execute_extension_call`, which runs the extension's code in a thread, with the
manifest's timeout.

An extension's code is a third party's. The call gives it only what it needs: its arguments, its own
settings and switches, and who called it, as an :class:`~smarter.apps.llmtool.extension.protocol.ExtensionCaller`.
It gets none of the platform's database objects, so that it can run in a worker without the database or
the platform's credentials (ADR-038). The one thing the executor still reads from the database is the
extension's code, its archive, the first time a process runs a version
(:func:`~smarter.apps.llmtool.extension.loader.load_by_key`).
"""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Final, Literal, Optional

from pydantic import Field, JsonValue, TypeAdapter, ValidationError

from smarter.apps.llmtool.runner import ToolCall, ToolCallResult
from smarter.lib import logging
from smarter.lib.django.connections import close_thread_connections
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .exceptions import SmarterExtensionLoadError
from .loader import load_by_key
from .manifest import describe_validation_errors
from .protocol import ExtensionCaller, ExtensionContext, ExtensionToolError
from .settings import settings_model

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])

EXTENSION_TOOL_CALL_KIND: Final = "extension"
"""The ``kind`` of an Extension's tool call, which selects :func:`execute_extension_call`."""

JSON_VALUE: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


class ExtensionToolCall(ToolCall):
    """
    An Extension's tool call, resolved for execution.

    .. warning::

        ``settings`` holds the extension's secret settings, decrypted. It is excluded from ``repr()``.
        Never log the call's ``model_dump()``.

    :ivar slug: The extension's slug.
    :ivar version: The installed version.
    :ivar sha256: The sha256 of the version's archive, which names its code.
    :ivar tool_name: The tool's own name, e.g. ``get_weather``.
    :ivar arguments: The LLM's arguments, validated, as JSON.
    :ivar settings: The extension's settings, by name, with secrets decrypted.
    :ivar switches: The extension's waffle switches, by their names in the manifest, and whether each is on.
    :ivar account_number: The account of the LLMClient that called the tool.
    :ivar user_id: The id of the user whose prompt called the tool.
    :ivar llmclient_name: The name of the LLMClient that called the tool.
    :ivar timeout: Seconds that the tool may run, from the manifest.
    """

    kind: Literal["extension"] = EXTENSION_TOOL_CALL_KIND
    slug: str
    version: str
    sha256: str
    tool_name: str
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    settings: dict[str, JsonValue] = Field(default_factory=dict, repr=False)
    switches: dict[str, bool] = Field(default_factory=dict)
    account_number: Optional[str] = None
    user_id: Optional[int] = None
    llmclient_name: Optional[str] = None
    timeout: float = 30


def run_tool(tool, validated, context: ExtensionContext, timeout: float) -> JsonValue:
    """
    Run an extension's tool in a thread of its own, with a timeout.

    :param tool: The tool's class.
    :param validated: Its validated arguments.
    :param context: Its context.
    :param timeout: Seconds that it may run.
    :returns: The tool's result, which must be JSON.
    :raises ExtensionToolError: With the message for the LLM, if the tool fails, times out, or returns
        a result that isn't JSON.
    """

    def call_tool() -> JsonValue:
        try:
            return tool().call(validated, context)
        finally:
            # the tool runs in its own thread, which has its own database connection.
            close_thread_connections()

    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"extension-{context.slug}")
    future = executor.submit(call_tool)
    try:
        result = future.result(timeout=timeout)
    except FutureTimeoutError:
        raise ExtensionToolError(f"The tool did not finish within {timeout:g} seconds.") from None
    except ExtensionToolError:
        raise
    # a tool is the extension's code, which can fail in any way at all.
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.exception("%s %s %s raised: %s", context.slug, context.version, tool.name, e)
        raise ExtensionToolError(f"The tool failed: {type(e).__name__}: {e}") from e
    finally:
        executor.shutdown(wait=False)
    try:
        value = JSON_VALUE.validate_python(result)
    except ValidationError as e:
        raise ExtensionToolError(f"The tool returned a result that is not JSON: {e.errors()[0]['msg']}") from e
    return value


def execute_extension_call(call: ToolCall) -> ToolCallResult:
    """
    Execute a resolved Extension tool call.

    :param call: The call, an :class:`ExtensionToolCall`.
    :returns: The tool's result; or a result with a ``failure``, the message for the LLM, when the
        extension can't be loaded, the tool doesn't exist, the arguments are invalid, or the tool fails,
        times out, or returns a result that isn't JSON.
    :raises TypeError: If the call isn't an :class:`ExtensionToolCall`.
    """
    if not isinstance(call, ExtensionToolCall):
        raise TypeError(f"execute_extension_call() needs an ExtensionToolCall, not a {type(call).__name__}.")
    try:
        loaded = load_by_key(call.slug, call.sha256)
    except SmarterExtensionLoadError as e:
        return ToolCallResult(failure=f"The extension could not be loaded: {e}")
    tool = loaded.tools.get(call.tool_name)
    if tool is None:
        return ToolCallResult(failure=f"{call.slug} {call.version} has no tool {call.tool_name}.")
    try:
        validated = tool.arguments_model.model_validate(call.arguments)
    except ValidationError as e:
        problems = describe_validation_errors(e, whole_location="arguments")
        return ToolCallResult(failure=f"Invalid arguments: {problems}")
    context = ExtensionContext(
        slug=call.slug,
        version=call.version,
        settings=settings_model(loaded.manifest)(**call.settings),
        caller=ExtensionCaller(
            account_number=call.account_number,
            user_id=call.user_id,
            llmclient_name=call.llmclient_name,
        ),
        switches=dict(call.switches),
    )
    try:
        value = run_tool(tool, validated, context, call.timeout)
    except ExtensionToolError as e:
        return ToolCallResult(failure=str(e))
    result = ToolCallResult(value=value)
    return result


__all__ = ["EXTENSION_TOOL_CALL_KIND", "ExtensionToolCall", "execute_extension_call", "run_tool"]
