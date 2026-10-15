"""Tests of smarter.apps.llmtool.extension.testing, the helpers for testing an extension's tools."""

from pydantic import SecretStr

from smarter.apps.llmtool.extension.testing import call_tool, tool_context
from smarter.lib.unittest.base_classes import SmarterTestBase

from .test_protocol import GetWeather


class TestTestingHelpers(SmarterTestBase):
    """Test calling a tool without installing its extension."""

    def test_tool_context(self):
        """The settings are attributes of the context's settings, with their types."""
        context = tool_context("weather", "1.0.0", google_maps_api_key=SecretStr("k"), region=None, retries=3)
        self.assertEqual(context.settings.google_maps_api_key.get_secret_value(), "k")  # type: ignore[attr-defined]
        self.assertIsNone(context.settings.region)  # type: ignore[attr-defined]
        self.assertEqual(context.settings.retries, 3)  # type: ignore[attr-defined]
        self.assertEqual((context.slug, context.version), ("weather", "1.0.0"))

    def test_call_tool(self):
        """A tool is called with validated arguments, from a dict or JSON, and invalid ones are an error."""
        self.assertEqual(call_tool(GetWeather, {"location": "Paris"}), {"location": "Paris"})
        self.assertEqual(call_tool(GetWeather, '{"location": "Paris"}'), {"location": "Paris"})
        self.assertIn("Invalid arguments", call_tool(GetWeather, "")["error"])  # type: ignore[index]
