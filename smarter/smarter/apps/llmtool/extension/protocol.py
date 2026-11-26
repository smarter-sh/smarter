"""
The protocol that a Smarter Extension's tools implement.

A tool is a subclass of :class:`SmarterExtensionTool`. It declares its name, the Pydantic
model of its arguments, and a :meth:`~SmarterExtensionTool.call` method:

.. code-block:: python

    from pydantic import BaseModel, Field

    from smarter.apps.llmtool.extension import ExtensionContext, ExtensionToolError, SmarterExtensionTool

    class WeatherArguments(BaseModel):
        location: str = Field(..., description="City and state, e.g. San Francisco, CA")

    class GetWeather(SmarterExtensionTool):
        \"\"\"Get the current weather and a 24-hour forecast for a location.\"\"\"

        name = "get_weather"
        arguments_model = WeatherArguments

        def call(self, arguments: WeatherArguments, context: ExtensionContext):
            api_key = context.settings.google_maps_api_key.get_secret_value()
            ...
            return {"location": arguments.location, "forecast": [...]}

The platform does everything else:

- the OpenAI tool definition: the class docstring is its description, and the arguments
  model's JSON schema is its parameters;
- parsing and validating the LLM's arguments, and returning validation errors to the LLM;
- the ``llm_tool_presented``, ``llm_tool_requested`` and ``llm_tool_responded`` signals;
- turning an exception into an ``{"error": ...}`` result, so that the LLM can recover;
- a timeout, from the manifest's ``[tool.smarter] timeout``.

Raise :class:`ExtensionToolError` to return a message to the LLM. Any other exception is
logged with its traceback, and the LLM is told that the tool failed.
"""

import inspect
import logging as python_logging
import re
from dataclasses import dataclass, field
from typing import ClassVar, Optional, Union

from pydantic import BaseModel, JsonValue

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,47}$")
"""A tool's name: letters, digits and underscores, starting with a letter, at most 48 characters."""
MAX_DESCRIPTION_LENGTH = 1024
"""The maximum length of a tool description offered to the LLM."""

ExtensionLogger = Union[python_logging.Logger, logging.WaffleSwitchedLoggerWrapper]
"""The logger of an extension's code."""


class ExtensionToolError(Exception):
    """
    Raised by a tool to tell the LLM why it could not do what was asked.

    The message is returned to the LLM as ``{"error": "<message>"}``, without a traceback.
    """


def switch_name(slug: str, name: str) -> str:
    """
    Return the waffle switch name of one of an extension's switches.

    :param slug: The extension's slug, e.g. ``date-calculator``.
    :param name: The switch's name in the manifest, e.g. ``logging``.
    :returns: e.g. ``ext_date_calculator_logging``.
    """
    return f"ext_{slug.replace('-', '_')}_{name}"


def extension_logger(slug: str) -> ExtensionLogger:
    """
    Return the logger of an extension's code, switched by ``SmarterWaffleSwitches.EXTENSION_LOGGING``.

    :param slug: The extension's slug.
    """
    return logging.getSmarterLogger(
        f"smarter_extensions.{slug}", any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING]
    )


@dataclass(frozen=True)
class ExtensionCaller:
    """
    Who called a tool: plain identifiers, not the platform's database objects.

    An extension's code is a third party's. It gets what identifies the caller, and nothing that would
    let it read or change the platform's data, or reach a user's personal details.

    :param account_number: The account of the LLMClient that called the tool, e.g. ``1234-5678-9012``.
    :param user_id: The id of the user whose prompt called the tool.
    :param llmclient_name: The name of the LLMClient that called the tool.
    """

    account_number: Optional[str] = None
    user_id: Optional[int] = None
    llmclient_name: Optional[str] = None


@dataclass(frozen=True)
class ExtensionContext:
    """
    What a tool call knows about where it runs.

    Everything here is a plain value, decided before the call: it reads no database, so that the
    tool can run in a worker without one (ADR-038).

    :param slug: The extension's slug.
    :param version: The extension's installed version.
    :param settings: The extension's settings, one attribute per setting in its manifest.
        A ``secret`` setting is a :class:`pydantic.SecretStr`; an unset setting is None.
    :param caller: Who called the tool: the account number, the user's id and the LLMClient's name.
    :param switches: The extension's own waffle switches, by their names in the manifest, and whether each is on.
    """

    slug: str
    version: str
    settings: BaseModel
    caller: ExtensionCaller = field(default_factory=ExtensionCaller)
    switches: dict[str, bool] = field(default_factory=dict)
    logger: ExtensionLogger = field(default=None, compare=False)  # type: ignore[assignment]

    def __post_init__(self):
        if self.logger is None:
            object.__setattr__(self, "logger", extension_logger(self.slug))

    def switch_is_active(self, name: str) -> bool:
        """
        Return whether one of the extension's waffle switches is on.

        :param name: The switch's name in the manifest's ``[[tool.smarter.switches]]``, without the ``ext_<slug>_`` prefix.
        :returns: True if the switch exists and is on, as it was when the tool was called.
        """
        return self.switches.get(name, False)


class SmarterExtensionTool:
    """
    The base class of a Smarter Extension's tools.

    Subclasses set :attr:`name` and :attr:`arguments_model`, document the tool in the class
    docstring (or set :attr:`description`), and implement :meth:`call`. A new instance is
    created for each tool call.
    """

    name: ClassVar[str]
    """The tool's name, unique within its extension, e.g. ``get_weather``."""

    arguments_model: ClassVar[type[BaseModel]]
    """The Pydantic model of the tool's arguments.

    Its JSON schema is the tool's parameters.
    """

    description: ClassVar[Optional[str]] = None
    """The tool's description for the LLM.

    Defaults to the class docstring.
    """

    cache_ttl: ClassVar[int] = 0
    """Seconds to cache the tool's results, by its arguments and the extension's settings.

    0, the default, caches nothing.

    Set it only for a tool that changes nothing, and whose result depends only on its arguments
    and settings, not on who calls it (``context.caller``): a cached result is returned to every
    LLMClient and user. For example,
    a weather forecast, ``cache_ttl = 3600``. An error is never cached.
    """

    def call(self, arguments: BaseModel, context: ExtensionContext) -> JsonValue:
        """
        Do what the LLM asked.

        :param arguments: The LLM's arguments, validated by :attr:`arguments_model`.
        :param context: The extension's settings, and who called the tool.
        :returns: The result for the LLM: any JSON value.
        :raises ExtensionToolError: To tell the LLM why the tool could not do what was asked.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.call() is not implemented")

    @classmethod
    def tool_description(cls) -> str:
        """The tool's description for the LLM: :attr:`description`, or the class docstring."""
        text = cls.description
        if not text:
            text = inspect.getdoc(cls)
        if not text:
            text = ""
        if not cls.description and inspect.getdoc(SmarterExtensionTool) == text:
            text = ""
        words = text.split()
        description = " ".join(words)
        return description[:MAX_DESCRIPTION_LENGTH]

    @classmethod
    def parameters(cls) -> SmarterDictType:
        """The tool's parameters for the LLM: the JSON schema of :attr:`arguments_model`."""
        schema = cls.arguments_model.model_json_schema()
        schema.pop("title", None)
        schema["type"] = "object"
        schema.setdefault("properties", {})
        return schema

    @classmethod
    def problems(cls) -> list[str]:
        """
        Explain why this class is not a valid tool, if it is not.

        :returns: A description of each problem; empty if the tool is valid.
        """
        problems: list[str] = []
        name = getattr(cls, "name", None)
        if not isinstance(name, str) or not TOOL_NAME_PATTERN.match(name):
            problems.append(
                f"{cls.__name__}.name must be letters, digits and underscores, starting with a letter, "
                f"at most 48 characters; got {name!r}"
            )
        model = getattr(cls, "arguments_model", None)
        if not (inspect.isclass(model) and issubclass(model, BaseModel)):
            problems.append(f"{cls.__name__}.arguments_model must be a pydantic BaseModel subclass")
        if cls.call is SmarterExtensionTool.call:
            problems.append(f"{cls.__name__} does not implement call()")
        if not cls.tool_description():
            problems.append(f"{cls.__name__} has no description: write a class docstring")
        return problems


__all__ = [
    "ExtensionCaller",
    "ExtensionContext",
    "ExtensionLogger",
    "ExtensionToolError",
    "SmarterExtensionTool",
    "extension_logger",
    "switch_name",
]
