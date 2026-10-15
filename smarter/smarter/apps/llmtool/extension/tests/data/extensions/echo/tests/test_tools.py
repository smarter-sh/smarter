"""The echo extension's own tests, run by manage.py test_extension."""

import unittest

from echo.tools import Echo, Fail, Refuse
from pydantic import SecretStr

from smarter.apps.llmtool.extension.testing import call_tool, tool_context


class TestEcho(unittest.TestCase):
    """Test the echo tool, without installing the extension."""

    def test_echo(self):
        context = tool_context("echo", greeting="hi", repeat=2, api_key=SecretStr("k"))
        self.assertEqual(call_tool(Echo, {"text": "x"}, context)["echo"], "hi x hi x")

    def test_errors(self):
        self.assertIn("Invalid arguments", call_tool(Echo, "{}")["error"])
        self.assertEqual(call_tool(Refuse, {}), {"error": "I refuse"})
        with self.assertRaises(RuntimeError):
            call_tool(Fail, {})
