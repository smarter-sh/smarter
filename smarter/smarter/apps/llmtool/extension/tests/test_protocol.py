"""Tests of smarter.apps.llmtool.extension.protocol."""

from types import SimpleNamespace

from pydantic import BaseModel, Field
from waffle.models import Switch

from smarter.apps.llmtool.extension.protocol import (
    ExtensionCaller,
    ExtensionContext,
    SmarterExtensionTool,
    switch_name,
)
from smarter.apps.llmtool.extension.settings import resolve_switches
from smarter.lib.unittest.base_classes import SmarterTestBase


class WeatherArguments(BaseModel):
    """The arguments of a weather tool."""

    location: str = Field(..., description="City and state, e.g. San Francisco, CA")


class GetWeather(SmarterExtensionTool):
    """
    Get the current weather.

    Use it for any location.
    """

    name = "get_weather"
    arguments_model = WeatherArguments

    def call(self, arguments, context):
        return {"location": arguments.location}


class TestSmarterExtensionTool(SmarterTestBase):
    """Test the base class of extension tools."""

    def test_tool_definition(self):
        """The docstring is the description, and the arguments model's schema is the parameters."""
        self.assertEqual(GetWeather.tool_description(), "Get the current weather. Use it for any location.")
        parameters = GetWeather.parameters()
        self.assertEqual(parameters["type"], "object")
        self.assertNotIn("title", parameters)
        self.assertEqual(parameters["required"], ["location"])
        self.assertEqual(GetWeather.problems(), [])

    def test_description_attribute(self):
        """An explicit description takes precedence over the docstring."""

        class Described(GetWeather):
            """Ignored."""

            description = "Explicit."

        self.assertEqual(Described.tool_description(), "Explicit.")

    def test_problems(self):
        """A tool without a valid name, arguments model, call() or description has problems."""

        class Invalid(SmarterExtensionTool):
            name = "not a name!"
            arguments_model = dict  # type: ignore[assignment]

        problems = Invalid.problems()
        self.assertEqual(len(problems), 4, problems)

    def test_call_not_implemented(self):
        """The base class's call() raises."""
        with self.assertRaises(NotImplementedError):
            SmarterExtensionTool().call(WeatherArguments(location="x"), None)  # type: ignore[arg-type]


class TestExtensionContext(SmarterTestBase):
    """Test the context of a tool call."""

    def test_logger_and_switches(self):
        """
        A context has the extension's logger, and reads its own switches from the values it was given.

        The app reads them from waffle, with resolve_switches(), before the call: the context reads no database.
        """

        class NoSettings(BaseModel):
            """An extension without settings."""

        context = ExtensionContext(slug="date-calculator", version="1.0.0", settings=NoSettings())
        self.assertIsNotNone(context.logger)
        self.assertFalse(context.switch_is_active("verbose"))
        context = ExtensionContext(
            slug="date-calculator", version="1.0.0", settings=NoSettings(), switches={"verbose": True}
        )
        self.assertTrue(context.switch_is_active("verbose"))
        self.assertFalse(context.switch_is_active("other"))

        name = switch_name("date-calculator", "verbose")
        self.assertEqual(name, "ext_date_calculator_verbose")
        manifest = SimpleNamespace(smarter=SimpleNamespace(switches=[SimpleNamespace(name="verbose")]))
        self.assertEqual(resolve_switches("date-calculator", manifest), {"verbose": False})  # type: ignore[arg-type]
        Switch.objects.create(name=name, active=True)
        try:
            self.assertEqual(resolve_switches("date-calculator", manifest), {"verbose": True})  # type: ignore[arg-type]
        finally:
            Switch.objects.filter(name=name).delete()

    def test_caller_is_plain_identifiers(self):
        """A context names its caller by plain identifiers, not the platform's database objects."""

        class NoSettings(BaseModel):
            """An extension without settings."""

        caller = ExtensionCaller(account_number="1234-5678-9012", user_id=7, llmclient_name="helper")
        context = ExtensionContext(slug="date-calculator", version="1.0.0", settings=NoSettings(), caller=caller)
        self.assertEqual(context.caller.account_number, "1234-5678-9012")
        self.assertEqual(context.caller.user_id, 7)
        self.assertEqual(context.caller.llmclient_name, "helper")
        self.assertFalse(hasattr(context, "account"))
        self.assertFalse(hasattr(context, "user_profile"))
        self.assertEqual(ExtensionContext(slug="x", version="1", settings=NoSettings()).caller, ExtensionCaller())
