"""Tests of smarter.apps.llmtool.extension.toolkit."""

from unittest.mock import patch

from waffle.models import Switch

from smarter.apps.llmtool.extension import toolkit as toolkit_module
from smarter.apps.llmtool.extension.exceptions import SmarterExtensionLoadError
from smarter.apps.llmtool.extension.toolkit import ExtensionToolkit
from smarter.apps.llmtool.signals import (
    extension_tool_called,
    extension_tool_failed,
    extension_tool_responded,
)

from .mixins import ExtensionTestMixin


class TestExtensionToolkit(ExtensionTestMixin):
    """Test offering extension tools to the LLM, and running their calls."""

    def setUp(self):
        super().setUp()
        self.extension = self.enable_echo()
        self.toolkit = ExtensionToolkit([self.extension], account=self.account, user_profile=self.user_profile).load()

    def test_tools(self):
        """Each tool is offered as ext_<slug>_<name>, with its description and parameters."""
        names = [tool["function"]["name"] for tool in self.toolkit.tools]
        self.assertEqual(
            sorted(names),
            ["ext_echo_echo", "ext_echo_fail", "ext_echo_refuse", "ext_echo_slow", "ext_echo_unserializable"],
        )
        echo = next(tool for tool in self.toolkit.tools if tool["function"]["name"] == "ext_echo_echo")
        self.assertEqual(echo["function"]["description"], "Echo the text that it is sent, after a greeting.")
        self.assertEqual(echo["function"]["parameters"]["required"], ["text"])
        self.assertTrue(self.toolkit.is_extension_function("ext_echo_echo"))
        self.assertFalse(self.toolkit.is_extension_function("get_weather"))
        self.assertEqual(self.toolkit.extension_for("ext_echo_echo"), self.extension)
        self.assertIsNone(self.toolkit.extension_for("nope"))
        self.assertEqual(self.toolkit.tool_name_for("ext_echo_echo"), "echo")
        self.assertIsNone(self.toolkit.tool_name_for("nope"))
        self.assertEqual(self.toolkit.loaded, [self.extension])
        self.assertEqual(self.toolkit.errors, {})

    def test_call(self):
        """A call validates its arguments, runs with the extension's settings and context, and sends signals."""
        received = []
        for signal in (extension_tool_called, extension_tool_responded):
            signal.connect(
                lambda **kwargs: received.append(kwargs["signal"]), weak=False, dispatch_uid=f"t{id(signal)}"
            )
        try:
            result = self.toolkit.call("ext_echo_echo", '{"text": "world"}')
        finally:
            for signal in (extension_tool_called, extension_tool_responded):
                signal.disconnect(dispatch_uid=f"t{id(signal)}")
        self.assertEqual(result, {"echo": "hello world", "has_api_key": True, "account": self.account.account_number})
        self.assertEqual(received, [extension_tool_called, extension_tool_responded])
        self.assertEqual(self.toolkit.call("ext_echo_echo", {"text": "dict"})["echo"], "hello dict")  # type: ignore[index]

    def test_call_with_switch(self):
        """A tool reads the extension's own switches."""
        Switch.objects.filter(name="ext_echo_verbose").update(active=True)
        self.assertEqual(self.toolkit.call("ext_echo_echo", {"text": "x"})["version"], "1.0.0")  # type: ignore[index]

    def test_errors_are_returned_to_the_llm(self):
        """Invalid arguments, exceptions, refusals, timeouts and non-JSON results are returned as errors."""
        failures = []
        extension_tool_failed.connect(lambda **kwargs: failures.append(kwargs["error"]), weak=False, dispatch_uid="tf")
        try:
            cases = {
                ("ext_echo_echo", "{not json"): "not valid JSON",
                ("ext_echo_echo", "{}"): "Invalid arguments: text",
                ("ext_echo_echo", '{"text": ""}'): "Invalid arguments",
                ("ext_echo_fail", None): "RuntimeError: this tool always fails",
                ("ext_echo_refuse", ""): "I refuse",
                ("ext_echo_slow", None): "did not finish within 2 seconds",
                ("ext_echo_unserializable", None): "not JSON",
                ("nope", None): "not an extension tool",
            }
            for (function_name, arguments), message in cases.items():
                with self.subTest(function_name=function_name, arguments=arguments):
                    result = self.toolkit.call(function_name, arguments)
                    self.assertIn(message, result["error"])  # type: ignore[index]
        finally:
            extension_tool_failed.disconnect(dispatch_uid="tf")
        self.assertEqual(len(failures), 7)

    def test_skipped_extensions(self):
        """Disabled, unavailable and broken extensions are skipped and reported."""
        self.installer.disable(self.extension)
        toolkit = ExtensionToolkit([self.extension]).load()
        self.assertEqual(toolkit.errors, {"echo": "the extension is disabled"})
        self.assertEqual(toolkit.tools, [])

        self.installer.enable(self.extension)
        self.extension.all_accounts = False
        self.extension.save()
        self.assertFalse(self.extension.is_available_to(None))
        toolkit = ExtensionToolkit([self.extension], account=self.account).load()
        self.assertEqual(toolkit.errors, {"echo": "the extension is not available to this account"})
        self.extension.accounts.add(self.account)
        self.assertEqual(len(ExtensionToolkit([self.extension], account=self.account).load().tools), 5)

        with patch.object(toolkit_module, "load_version", side_effect=SmarterExtensionLoadError("cannot import")):
            toolkit = ExtensionToolkit([self.extension], account=self.account).load()
        self.assertEqual(toolkit.errors, {"echo": "cannot import"})

    def test_function_name(self):
        """Function names are at most 64 characters, and unique."""
        name = self.toolkit.function_name("a-very-long-extension-slug-that-is-long", "and_a_very_long_tool_name_too")
        self.assertLessEqual(len(name), 64)
        self.assertTrue(name.startswith("ext_a_very_long"))
        self.assertNotEqual(self.toolkit.function_name("echo", "echo"), "ext_echo_echo")
