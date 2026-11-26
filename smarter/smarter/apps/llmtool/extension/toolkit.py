"""
The extension tools that a prompt offers the LLM.

:class:`ExtensionToolkit` turns an LLMClient's extensions into what an OpenAI-compatible
chat completion needs:

- **tools**: one function tool per extension tool, named ``ext_<slug>_<tool name>``, with
  the tool's description and its arguments model's JSON schema;
- **tool calls**: :meth:`ExtensionToolkit.call` validates the LLM's arguments, runs the
  tool with a timeout, and returns its result. Errors are returned to the LLM as
  ``{"error": ...}``, so that it can recover, rather than failing the prompt. A tool that
  sets :attr:`~.protocol.SmarterExtensionTool.cache_ttl` has its results cached.

An extension that is disabled, not available to the LLMClient's account, or whose code does
not load, is skipped and reported in :attr:`ExtensionToolkit.errors`, so that one broken
extension does not fail the prompt.
"""

import hashlib
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union

from pydantic import JsonValue, ValidationError

from smarter.apps.llmtool.runner import get_tool_runner
from smarter.common.conf import smarter_settings
from smarter.lib import json, logging
from smarter.lib.cache.tool_results import cached_tool_call
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from ..signals import (
    extension_tool_called,
    extension_tool_completed,
    extension_tool_failed,
    extension_tool_responded,
)
from .exceptions import SmarterExtensionLoadError
from .execution import ExtensionToolCall
from .loader import LoadedExtension, load_version, publish_archive
from .manifest import describe_validation_errors
from .protocol import SmarterExtensionTool
from .settings import resolve_settings, resolve_switches, settings_values

if TYPE_CHECKING:
    from smarter.apps.account.models import Account, UserProfile
    from smarter.apps.llmtool.models import Extension

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])

FUNCTION_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]")
MAX_FUNCTION_NAME_LENGTH = 64
"""The maximum length of an OpenAI function name."""
FUNCTION_NAME_PREFIX = "ext_"
TOOL_CACHE_NAMESPACE = "extension"
"""The namespace of extension tool results in :func:`~smarter.lib.cache.tool_results.cached_tool_call`."""


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
                logger.warning("skipping extension %s: %s", extension.slug, e)
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
            problems = describe_validation_errors(e, whole_location="arguments")
            raise ExtensionToolCallError(f"Invalid arguments: {problems}") from e
        settings = resolve_settings(function.extension, function.loaded.manifest)
        if smarter_settings.app_llmtool_tool_runner == "remote" and function.extension.installed_version:
            # the tool worker has no database: it loads the extension's code from the cache.
            publish_archive(function.extension.installed_version)
        call = ExtensionToolCall(
            slug=slug,
            version=version,
            sha256=function.loaded.sha256,
            tool_name=tool_name,
            arguments=validated.model_dump(mode="json"),
            settings=settings_values(settings),
            switches=resolve_switches(slug, function.loaded.manifest),
            account_number=self.account.account_number if self.account else None,
            user_id=self.user_profile.user_id if self.user_profile else None,  # type: ignore[attr-defined]
            llmclient_name=getattr(self.llmclient, "name", None),
            timeout=function.loaded.manifest.smarter.timeout,
        )
        # a hash of the settings, so that changing one invalidates the tool's cached results. A
        # secret setting is hashed as SecretStr dumps it, masked, so no secret is part of the key.
        settings_hash = hashlib.sha256(settings.model_dump_json().encode()).hexdigest()[:16]
        result = cached_tool_call(
            TOOL_CACHE_NAMESPACE,
            (function.extension.pk, version, tool_name, settings_hash),
            validated,
            function.tool.cache_ttl,
            lambda: self.execute(call),
        )
        extension_tool_responded.send(
            sender=self.__class__,
            slug=slug,
            version=version,
            tool_name=tool_name,
            characters=len(json.dumps(result.value)),
            cached=result.cached,
        )
        return result.value

    def execute(self, call: ExtensionToolCall) -> JsonValue:
        """
        Run a resolved tool call with the tool runner (:mod:`smarter.apps.llmtool.runner`).

        :param call: The call, with its validated arguments, settings, switches and caller.
        :returns: The tool's result.
        :raises ExtensionToolCallError: If the tool fails, times out, or returns a result that is not
            JSON. Raised, rather than returned, so that an error is never cached.
        """
        result = get_tool_runner().run(call)
        if result.failure is not None:
            raise ExtensionToolCallError(result.failure)
        return result.value

    def failed(self, function: ExtensionFunction, error: str) -> SmarterDictType:
        """
        Report a failed tool call, and return the error for the LLM.

        Sends ``extension_tool_failed``, and logs a warning.

        :param function: The tool that failed.
        :param error: Why it failed.
        :returns: ``{"error": error}``.
        """
        extension_tool_failed.send(
            sender=self.__class__,
            slug=function.extension.slug,
            version=function.loaded.version,
            tool_name=function.tool.name,
            error=error,
        )
        return {"error": error}


__all__ = ["ExtensionFunction", "ExtensionToolCallError", "ExtensionToolkit"]
