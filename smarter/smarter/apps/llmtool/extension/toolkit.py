"""
The extension tools that a prompt offers the LLM.

:class:`ExtensionToolkit` turns an LLMClient's extensions into what an OpenAI-compatible
chat completion needs:

- **tools**: one function tool per extension tool, named ``ext_<slug>_<tool name>``, with
  the tool's description and its arguments model's JSON schema;
- **tool calls**: :meth:`ExtensionToolkit.call` validates the LLM's arguments, runs the
  tool with a timeout, and returns its result. Errors are returned to the LLM as
  ``{"error": ...}``, so that it can recover, rather than failing the prompt.

An extension that is disabled, not available to the LLMClient's account, or whose code does
not load, is skipped and reported in :attr:`ExtensionToolkit.errors`, so that one broken
extension does not fail the prompt.
"""

import hashlib
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union

from django.db import connections
from pydantic import JsonValue, TypeAdapter, ValidationError

from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from ..signals import (
    extension_tool_called,
    extension_tool_completed,
    extension_tool_failed,
    extension_tool_responded,
)
from .exceptions import SmarterExtensionLoadError
from .loader import LoadedExtension, load_version
from .protocol import ExtensionContext, ExtensionToolError, SmarterExtensionTool
from .settings import resolve_settings

if TYPE_CHECKING:
    from smarter.apps.account.models import Account, UserProfile
    from smarter.apps.llmtool.models import Extension

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])

FUNCTION_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]")
MAX_FUNCTION_NAME_LENGTH = 64
"""The maximum length of an OpenAI function name."""
FUNCTION_NAME_PREFIX = "ext_"
JSON_VALUE = TypeAdapter(JsonValue)


class ExtensionToolCallError(Exception):
    """A tool call failed.

    :meth:`ExtensionToolkit.call` returns its message to the LLM.
    """


@dataclass(frozen=True)
class ExtensionFunction:
    """A function tool offered to the LLM, and the extension tool it calls."""

    name: str
    extension: "Extension"
    loaded: LoadedExtension
    tool: type[SmarterExtensionTool]


class ExtensionToolkit:
    """
    The extension tools and tool call dispatch of one prompt.

    :param extensions: The LLMClient's extensions.
    :param account: The LLMClient's account, which an extension must be available to.
    :param user_profile: The user whose prompt this is.
    :param llmclient: The LLMClient.

    **Example usage**::

        toolkit = ExtensionToolkit(LLMClientExtensions.extensions_for(llmclient), account=account).load()
        tools.extend(toolkit.tools)
        ...
        if toolkit.is_extension_function(tool_call.function.name):
            result = toolkit.call(tool_call.function.name, arguments)
    """

    def __init__(
        self,
        extensions: list["Extension"],
        account: Optional["Account"] = None,
        user_profile: Optional["UserProfile"] = None,
        llmclient: Optional[object] = None,
    ):
        self.extensions = extensions
        self.account = account
        self.user_profile = user_profile
        self.llmclient = llmclient
        self.tools: list[SmarterDictType] = []
        self.functions: dict[str, ExtensionFunction] = {}
        self.errors: dict[str, str] = {}
        self.loaded: list["Extension"] = []

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return logging.formatted_text(f"{__name__}.{self.__class__.__name__}")

    def function_name(self, slug: str, tool_name: str) -> str:
        """
        Return a unique OpenAI function name for one of an extension's tools.

        The name is ``ext_<slug>_<tool name>``, with the slug's hyphens replaced by underscores,
        and at most 64 characters long. If two tools would have the same name, a short hash
        is appended.

        :param slug: The extension's slug.
        :param tool_name: The tool's name.
        :returns: The function name.
        """
        name = FUNCTION_NAME_PATTERN.sub("_", f"{FUNCTION_NAME_PREFIX}{slug.replace('-', '_')}_{tool_name}")
        candidate = name[:MAX_FUNCTION_NAME_LENGTH]
        if candidate in self.functions or len(name) > MAX_FUNCTION_NAME_LENGTH:
            suffix = "_" + hashlib.sha256(name.encode()).hexdigest()[:6]
            candidate = candidate[: MAX_FUNCTION_NAME_LENGTH - len(suffix)] + suffix
        return candidate

    def load(self) -> "ExtensionToolkit":
        """
        Load each enabled extension's code, if this process has not already, and build its tools.

        :returns: This toolkit.
        """
        for extension in self.extensions:
            if not extension.enabled or extension.installed_version is None:
                self.errors[extension.slug] = "the extension is disabled"
                continue
            if not extension.is_available_to(self.account):
                self.errors[extension.slug] = "the extension is not available to this account"
                continue
            try:
                loaded = load_version(extension.installed_version)
            except SmarterExtensionLoadError as e:
                self.errors[extension.slug] = e.message
                logger.warning("%s.load() skipping extension %s: %s", self.formatted_class_name, extension.slug, e)
                continue
            self.loaded.append(extension)
            for tool in loaded.tools.values():
                function = ExtensionFunction(
                    name=self.function_name(extension.slug, tool.name), extension=extension, loaded=loaded, tool=tool
                )
                self.functions[function.name] = function
                self.tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": function.name,
                            "description": tool.tool_description(),
                            "parameters": tool.parameters(),
                        },
                    }
                )
        return self

    def is_extension_function(self, function_name: str) -> bool:
        """Return whether a function name is one of this toolkit's tools."""
        return function_name in self.functions

    def extension_for(self, function_name: str) -> Optional["Extension"]:
        """Return the extension of one of this toolkit's tools."""
        function = self.functions.get(function_name)
        return function.extension if function else None

    def tool_name_for(self, function_name: str) -> Optional[str]:
        """Return the extension tool's own name, e.g. ``get_weather``, of one of this toolkit's functions."""
        function = self.functions.get(function_name)
        return function.tool.name if function else None

    def call(self, function_name: str, arguments: Union[SmarterDictType, str, None] = None) -> JsonValue:
        """
        Run a tool call, and return its result for the LLM.

        Errors, including invalid arguments, an exception and a timeout, are returned as
        ``{"error": "..."}``, so that the LLM can recover.

        Sends ``extension_tool_called``, then ``extension_tool_responded`` or
        ``extension_tool_failed``, and always ``extension_tool_completed`` last.

        :param function_name: The function name that the LLM called.
        :param arguments: The function's arguments, as a dict or a JSON string.
        :returns: The tool's result.
        """
        function = self.functions.get(function_name)
        if function is None:
            return {"error": f"{function_name} is not an extension tool."}
        start_time = time.monotonic()
        success = False
        try:
            result = self.run(function, arguments)
            success = True
            return result
        except ExtensionToolCallError as e:
            return self.failed(function, str(e))
        finally:
            extension_tool_completed.send(
                sender=self.__class__,
                slug=function.extension.slug,
                version=function.loaded.version,
                tool_name=function.tool.name,
                success=success,
                duration=time.monotonic() - start_time,
            )

    def run(self, function: ExtensionFunction, arguments: Union[SmarterDictType, str, None]) -> JsonValue:
        """
        Run one of this toolkit's tools, for :meth:`call`.

        :param function: The function that the LLM called.
        :param arguments: The function's arguments, as a dict or a JSON string.
        :returns: The tool's result.
        :raises ExtensionToolCallError: If the arguments are invalid, or the tool fails, times out,
            or returns a result that is not JSON.
        """
        slug, version, tool_name = function.extension.slug, function.loaded.version, function.tool.name
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except json.JSONDecodeError as e:
                raise ExtensionToolCallError(f"The arguments are not valid JSON: {e}") from e
        arguments = arguments if isinstance(arguments, dict) else {}
        extension_tool_called.send(
            sender=self.__class__, slug=slug, version=version, tool_name=tool_name, arguments=arguments
        )
        try:
            validated = function.tool.arguments_model.model_validate(arguments)
        except ValidationError as e:
            problems = "; ".join(
                f"{'.'.join(str(part) for part in error['loc']) or 'arguments'}: {error['msg']}" for error in e.errors()
            )
            raise ExtensionToolCallError(f"Invalid arguments: {problems}") from e
        context = ExtensionContext(
            slug=slug,
            version=version,
            settings=resolve_settings(function.extension, function.loaded.manifest),
            account=self.account,
            user_profile=self.user_profile,
            llmclient=self.llmclient,
        )
        timeout = function.loaded.manifest.smarter.timeout

        def run_tool() -> JsonValue:
            try:
                return function.tool().call(validated, context)
            finally:
                # the tool runs in its own thread, which has its own database connection.
                connections.close_all()

        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"extension-{slug}")
        future = executor.submit(run_tool)
        try:
            result = future.result(timeout=timeout)
        except FutureTimeoutError:
            raise ExtensionToolCallError(f"The tool did not finish within {timeout} seconds.") from None
        except ExtensionToolError as e:
            raise ExtensionToolCallError(str(e)) from e
        # a tool is the extension's code, which can fail in any way at all.
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.exception("%s.run() %s %s %s raised: %s", self.formatted_class_name, slug, version, tool_name, e)
            raise ExtensionToolCallError(f"The tool failed: {type(e).__name__}: {e}") from e
        finally:
            executor.shutdown(wait=False)
        try:
            result = JSON_VALUE.validate_python(result)
        except ValidationError as e:
            raise ExtensionToolCallError(f"The tool returned a result that is not JSON: {e.errors()[0]['msg']}") from e
        characters = len(json.dumps(result))
        extension_tool_responded.send(
            sender=self.__class__, slug=slug, version=version, tool_name=tool_name, characters=characters
        )
        return result

    def failed(self, function: ExtensionFunction, error: str) -> SmarterDictType:
        """Report a failed tool call, and return the error for the LLM."""
        extension_tool_failed.send(
            sender=self.__class__,
            slug=function.extension.slug,
            version=function.loaded.version,
            tool_name=function.tool.name,
            error=error,
        )
        logger.warning(
            "%s.call() %s %s failed in thread %s: %s",
            self.formatted_class_name,
            function.extension.slug,
            function.tool.name,
            threading.current_thread().name,
            error,
        )
        return {"error": error}


__all__ = ["ExtensionFunction", "ExtensionToolCallError", "ExtensionToolkit"]
