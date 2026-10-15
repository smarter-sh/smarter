"""
Helpers for testing an extension's tools, without installing the extension.

An extension's tests call its tools directly, with the settings they need, and without the
database or an LLM:

.. code-block:: python

    from pydantic import SecretStr

    from smarter.apps.llmtool.extension.testing import call_tool, tool_context
    from weather.tools import GetWeather

    class TestGetWeather(unittest.TestCase):
        def test_unknown_place(self):
            context = tool_context("weather", google_maps_api_key=SecretStr("test-key"))
            with patch("weather.services.googlemaps.Client") as client:
                client.return_value.geocode.return_value = []
                result = call_tool(GetWeather, {"location": "Atlantis"}, context)
            self.assertIn("Could not find Atlantis", result["error"])

Run an extension repository's tests in a Smarter development container with
``manage.py test_extension <path>``, which puts the repository on ``sys.path``, so that its tests
import its package by name.
"""

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError, create_model

from .protocol import ExtensionContext, ExtensionToolError, SmarterExtensionTool
from .settings import ResolvedSettingValue


class TestSettings(BaseModel):
    """The base class of the settings that :func:`tool_context` builds."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)


def tool_context(slug: str = "test", version: str = "0.0.0", **settings: ResolvedSettingValue) -> ExtensionContext:
    """
    Return the context of a tool call, with the given settings.

    :param slug: The extension's slug, which names its logger and switches.
    :param version: The extension's version.
    :param settings: The settings, by name, as the tool reads them, e.g. ``api_key=SecretStr("x")``.
    :returns: A context without an account, user or LLMClient.
    """
    fields: dict[str, tuple[type, ResolvedSettingValue]] = {
        name: (type(value) if value is not None else Optional[str], value)  # type: ignore[misc]
        for name, value in settings.items()
    }
    model = create_model("Settings", __base__=TestSettings, **fields)  # type: ignore[call-overload]
    return ExtensionContext(slug=slug, version=version, settings=model())


def call_tool(
    tool: type[SmarterExtensionTool],
    arguments: Union[dict, str],
    context: Optional[ExtensionContext] = None,
) -> JsonValue:
    """
    Call a tool as the platform does: validate its arguments, run it, and turn its errors into results.

    Unlike the platform, it runs the tool in the calling thread, without a timeout, and lets
    unexpected exceptions propagate, so that a test sees them.

    :param tool: The tool's class.
    :param arguments: The LLM's arguments, as a dict or a JSON string.
    :param context: The context; :func:`tool_context` with no settings if omitted.
    :returns: The tool's result, or ``{"error": ...}`` for invalid arguments or an :class:`ExtensionToolError`.
    """
    try:
        if isinstance(arguments, str):
            validated = tool.arguments_model.model_validate_json(arguments or "{}")
        else:
            validated = tool.arguments_model.model_validate(arguments)
    except ValidationError as e:
        return {"error": f"Invalid arguments: {e.errors()[0]['msg']}"}
    try:
        return tool().call(validated, context or tool_context())
    except ExtensionToolError as e:
        return {"error": str(e)}


__all__ = ["TestSettings", "call_tool", "tool_context"]
