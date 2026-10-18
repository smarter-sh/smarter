"""Unit tests of OpenAISmarterClient's error formatting, budget refusals, MCP tools and guard clauses, on a client without its handler state."""

from unittest.mock import MagicMock, PropertyMock, patch

from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from smarter.apps.account.models.budget import SmarterBudgetExceeded
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.services.text_completion.lib import (
    chat_provider_base as base_module,
)
from smarter.apps.provider.services.text_completion.lib import (
    openai_compatible_chat_provider as module,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    OpenAISmarterClient,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

PLUGIN_PREFIX = smarter_settings.function_calling_identifier_prefix


def chat_completion(content: str) -> ChatCompletion:
    """Return a ChatCompletion whose single message has the given content."""
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-test",
            "choices": [
                {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}},
            ],
        }
    )


class TestOpenAISmarterClientUnits(SmarterTestBase):
    """Test OpenAISmarterClient methods that need only a little of the handler's state."""

    def setUp(self):
        super().setUp()
        self.client = OpenAISmarterClient.__new__(OpenAISmarterClient)
        self.client._base_url = "https://api.example.com/v1/"
        self.client._messages = [{"role": "system", "content": "You are a test."}]
        self.client.mcp_toolkit = None
        self.client.tools = None
        self.client.available_functions = None
        self.client._chat = None
        patcher = patch.object(OpenAISmarterClient, "append_message")
        self.append_message = patcher.start()
        self.addCleanup(patcher.stop)

    def appended(self) -> list[str]:
        return [call.kwargs.get("content") for call in self.append_message.call_args_list]

    # -------------------------------------------------------------------------
    # append_openai_error_response
    # -------------------------------------------------------------------------
    def test_error_response_with_an_embedded_error_object(self):
        """An error object embedded in the provider's message is pretty-printed."""
        response = chat_completion("Error code: 400 - {'error': {'message': 'bad request'}}")
        self.client.append_openai_error_response(response, e=ValueError("bad"))
        content = self.appended()[0]
        self.assertIn("raised the following ValueError exception", content)
        self.assertIn('"message": "bad request"', content)
        self.assertIn("Python Stack trace", content)

    def test_error_response_without_an_error_object(self):
        """A message without a parseable object is kept as is."""
        response = chat_completion("Error code: 500 - {not a python literal}")
        self.client.append_openai_error_response(response, e=ValueError("bad"))
        self.assertTrue(self.appended()[0].startswith("Error code: 500 - {not a python literal}"))

    # -------------------------------------------------------------------------
    # tool_budget_refusal
    # -------------------------------------------------------------------------
    def test_budget_refusal_for_builtin_and_unknown_tools(self):
        """Extension tools and plugins that can't be found are never refused."""
        self.assertIsNone(self.client.tool_budget_refusal("ext_weather_get_weather"))
        self.assertIsNone(self.client.tool_budget_refusal(f"{PLUGIN_PREFIX}_not_a_number"))
        self.assertIsNone(self.client.tool_budget_refusal(f"{PLUGIN_PREFIX}_2147483646"))

    def test_budget_refusal_for_a_plugin(self):
        """A plugin whose budget is exceeded is refused with a json error, and is otherwise allowed."""
        plugin_meta = MagicMock(record_locator="plugin:test")
        with patch.object(module.PluginMeta, "get_cached_object", return_value=plugin_meta):
            with patch.object(module, "charge_authorization"):
                self.assertIsNone(self.client.tool_budget_refusal(f"{PLUGIN_PREFIX}_1"))
            with patch.object(module, "charge_authorization", side_effect=SmarterBudgetExceeded("over budget")):
                refusal = json.loads(self.client.tool_budget_refusal(f"{PLUGIN_PREFIX}_1"))
        self.assertEqual(refusal["error"], "budget_exceeded")

    def test_budget_refusal_for_an_mcp_tool(self):
        """An MCP tool's server is checked against its budget."""
        self.client.mcp_toolkit = MagicMock()
        self.client.mcp_toolkit.is_mcp_function.return_value = True
        self.client.mcp_toolkit.mcpclient_for.return_value = MagicMock(record_locator="mcpclient:test")
        with patch.object(module, "charge_authorization") as authorize:
            self.assertIsNone(self.client.tool_budget_refusal("mcp_tool"))
        authorize.assert_called_once()

    # -------------------------------------------------------------------------
    # tool_display_name
    # -------------------------------------------------------------------------
    def test_tool_display_name_of_a_plugin(self):
        """A plugin's symbolic function name is displayed as its PluginMeta's name."""
        plugin_meta = MagicMock()
        plugin_meta.name = "stackademy_sql"
        with patch.object(module.PluginMeta, "get_cached_object", return_value=plugin_meta) as get:
            self.assertEqual(self.client.tool_display_name(f"{PLUGIN_PREFIX}_0000000016"), "stackademy_sql")
        get.assert_called_once_with(pk=16)

    def test_tool_display_name_of_unknown_tools(self):
        """Unknown functions, and plugins that can't be found, keep their function names."""
        for name in ("calculator", f"{PLUGIN_PREFIX}_not_a_number", f"{PLUGIN_PREFIX}_2147483646"):
            with self.subTest(name=name):
                self.assertEqual(self.client.tool_display_name(name), name)

    def test_tool_display_name_of_an_extension_tool(self):
        """An extension function is displayed as its tool's own name."""
        self.client.extension_toolkit = MagicMock()
        self.client.extension_toolkit.is_extension_function.return_value = True
        self.client.extension_toolkit.tool_name_for.return_value = "get_weather"
        self.addCleanup(setattr, self.client, "extension_toolkit", None)
        self.assertEqual(self.client.tool_display_name("ext_weather_get_weather"), "get_weather")

    def test_tool_display_name_of_an_mcp_tool(self):
        """An MCP function is displayed as its MCP tool's name."""
        self.client.mcp_toolkit = MagicMock()
        self.client.mcp_toolkit.is_mcp_function.return_value = True
        self.client.mcp_toolkit.functions = {"mcp1_search_code": MagicMock(tool_name="search_code")}
        self.assertEqual(self.client.tool_display_name("mcp1_search_code"), "search_code")

    # -------------------------------------------------------------------------
    # handle_mcp_clients
    # -------------------------------------------------------------------------
    def mcp_toolkit(self) -> MagicMock:
        connected = MagicMock()
        connected.name = "weather_server"
        toolkit = MagicMock()
        toolkit.load.return_value = toolkit
        toolkit.tools = [{"type": "function", "function": {"name": "mcp_weather"}}]
        toolkit.functions = {"mcp_weather": MagicMock()}
        toolkit.system_prompt.return_value = "Use the weather server."
        toolkit.connected = [connected]
        toolkit.errors = {"down_server": "connection refused"}
        return toolkit

    def handle_mcp_clients(self, toolkit: MagicMock, with_mcpclients: bool = True):
        self.client._chat = MagicMock(spec=Prompt)
        mcpclients = [MagicMock()] if with_mcpclients else []
        with patch("smarter.apps.llmclient.models.LLMClientMCPClients.mcpclients_for", return_value=mcpclients):
            with patch.object(module, "MCPToolkit", return_value=toolkit):
                self.client.handle_mcp_clients()

    def test_mcp_tools_and_instructions_are_added(self):
        """The MCP tools are offered, their instructions extend the system prompt, and the servers are reported."""
        self.handle_mcp_clients(self.mcp_toolkit())
        self.assertEqual(self.client.tools, [{"type": "function", "function": {"name": "mcp_weather"}}])
        self.assertIn("mcp_weather", self.client.available_functions)
        self.assertEqual(self.client.messages[0]["content"], "You are a test.\n\nUse the weather server.")
        appended = self.appended()
        self.assertTrue(any("weather_server" in content for content in appended))
        self.assertTrue(any("down_server" in content for content in appended))

    def test_mcp_instructions_without_a_system_prompt(self):
        """Without a system message, the instructions become one."""
        self.client._messages = [{"role": "user", "content": "hi"}]
        self.handle_mcp_clients(self.mcp_toolkit())
        self.assertEqual(self.client.messages[0], {"role": "system", "content": "Use the weather server."})

    def test_no_mcp_clients(self):
        """Without MCP clients, or without a prompt, there's no toolkit."""
        self.handle_mcp_clients(self.mcp_toolkit(), with_mcpclients=False)
        self.assertIsNone(self.client.mcp_toolkit)
        self.client._chat = None
        self.client.handle_mcp_clients()
        self.assertIsNone(self.client.mcp_toolkit)

    # -------------------------------------------------------------------------
    # guard clauses
    # -------------------------------------------------------------------------
    def test_new_messages(self):
        """New_messages is empty without messages, and falls back to every message when the flag is missing."""
        self.client._messages = None
        self.assertEqual(self.client.new_messages, [])
        self.client._messages = [{"role": "user", "content": "hi"}]
        self.assertEqual(self.client.new_messages, self.client._messages)

    def test_process_tool_call_errors(self):
        """A tool call must be a function tool call, of an available function."""
        with self.assertRaises(SmarterValueError):
            self.client.process_tool_call({"not": "a tool call"})  # type: ignore[arg-type]
        self.client.available_functions = {}
        tool_call = ChatCompletionMessageToolCall(
            id="call_1", type="function", function=Function(name="no_such_function", arguments="{}")
        )
        with self.assertRaises(SmarterConfigurationError):
            self.client.process_tool_call(tool_call)

    def test_prep_second_request_needs_a_dict(self):
        self.client.second_iteration = None
        with self.assertRaises(SmarterValueError):
            self.client.prep_second_request()

    def test_second_request_offers_no_tools(self):
        """
        Test that only the first request offers tools, so the LLM can't chain one tool call on another's result.

        LLMClients that need several tools must ask for them together, in the first response, as
        llmclient-weather.yaml does. Update that prompt if this changes.
        """
        self.prep_first_request([{"type": "function", "function": {"name": "get_weather", "description": "Weather."}}])
        self.assertIn("tools", self.client.first_iteration["request"])
        self.client.second_iteration = {}
        self.client.prep_second_request()
        self.assertNotIn("tools", self.client.second_iteration["request"])
        self.assertNotIn("tool_choice", self.client.second_iteration["request"])

    def test_handle_response_needs_a_response_with_usage(self):
        """Handle_response needs a response, and the response needs usage."""
        self.client.iteration = 1
        self.client.first_response = None
        with self.assertRaises(SmarterValueError):
            self.client.handle_response()
        self.client.first_response = chat_completion("hi")
        with self.assertRaises(SmarterValueError):
            self.client.handle_response()

    def test_markdown_instructions_are_added_to_the_system_prompt(self):
        """The request's system prompt says that responses may use Markdown, without changing the history."""
        self.client.iteration = 1
        self.client._messages = [
            {"role": "system", "content": "You are a test.", "smarter_is_new": False},
            {"role": "user", "content": "hello", "smarter_is_new": True},
        ]
        messages = self.client.openai_messages
        self.assertEqual(messages[0]["content"], f"You are a test.\n\n{module.MARKDOWN_SYSTEM_PROMPT}")
        self.assertEqual(messages[1], {"role": "user", "content": "hello"})
        self.assertEqual(self.client._messages[0]["content"], "You are a test.")

    def test_markdown_instructions_without_a_system_prompt(self):
        """A thread without a system prompt gets one, with the Markdown instructions."""
        messages = OpenAISmarterClient.add_markdown_system_prompt([{"role": "user", "content": "hello"}])
        self.assertEqual(messages[0], {"role": "system", "content": module.MARKDOWN_SYSTEM_PROMPT})
        self.assertEqual(len(messages), 2)

    def test_markdown_instructions_are_added_once(self):
        """A system prompt that already has the Markdown instructions is unchanged."""
        messages = [{"role": "system", "content": module.MARKDOWN_SYSTEM_PROMPT}]
        self.assertEqual(OpenAISmarterClient.add_markdown_system_prompt(messages), messages)

    def test_messages_must_be_a_list(self):
        """The request messages need a message list."""
        self.client._messages = None
        with self.assertRaises(SmarterValueError):
            _ = self.client.openai_messages

    # -------------------------------------------------------------------------
    # prep_first_request: Smarter UI messages for the tools presented
    # -------------------------------------------------------------------------
    def prep_first_request(self, tools: list):
        self.client.tools = tools
        self.client.first_iteration = {}
        self.client.iteration = 1
        properties = {
            "base_url": "https://api.example.com/v1/",
            "api_key": "sk-test",
            "model": "gpt-test",
            "openai_messages": [],
            "url": "https://api.example.com/v1/",
            "provider_name": "test",
            "temperature": 0.5,
            "max_completion_tokens": 100,
            "prompt": None,
        }
        patchers = [
            patch.object(OpenAISmarterClient, name, new_callable=PropertyMock, return_value=value)
            for name, value in properties.items()
        ]
        patchers.append(patch.object(module, "chat_request"))
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client.prep_first_request()

    def test_tools_are_presented(self):
        """Each tool is presented with its inputs, and incomplete tool definitions are tolerated."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the weather.",
                    "parameters": {
                        "properties": {
                            "location": {"description": "A city."},
                            "unit": {"enum": ["Celsius", "Fahrenheit"]},
                        }
                    },
                },
            },
            {"type": "function", "function": {}},
            {},
        ]
        self.prep_first_request(tools)
        presented = [content for content in self.appended() if content.startswith("Tool presented")]
        self.assertEqual(len(presented), 3)
        self.assertIn("location: A city., unit: Celsius, Fahrenheit", presented[0])

    def test_a_plugin_is_presented_by_its_name(self):
        """A plugin's tool is presented by its PluginMeta's name, and its definition keeps its function name."""
        function_name = f"{PLUGIN_PREFIX}_0000000022"
        plugin_meta = MagicMock()
        plugin_meta.name = "stackademy_api"
        tools = [{"type": "function", "function": {"name": function_name, "description": "Stackademy's api."}}]
        with patch.object(module.PluginMeta, "get_cached_object", return_value=plugin_meta):
            self.prep_first_request(tools)
        presented = [content for content in self.appended() if content.startswith("Tool presented")]
        self.assertEqual(len(presented), 1)
        self.assertTrue(presented[0].startswith("Tool presented: stackademy_api() - Stackademy's api."), presented[0])
        self.assertIn(f'"name": "{function_name}"', presented[0])

    def test_a_called_plugin_is_named_by_its_name(self):
        """The tool call's message names a plugin by its PluginMeta's name, and its json keeps its function name."""
        function_name = f"{PLUGIN_PREFIX}_0000000022"
        tool_call = self.tool_call(function_name, '{"course": "CS210"}')
        with patch.object(OpenAISmarterClient, "provider_name", new_callable=PropertyMock, return_value="openai"):
            self.client.append_message_tool_called(tool_call, tool_name="stackademy_api")
            self.client.append_message_tool_called(tool_call)
        named, unnamed = self.appended()
        self.assertTrue(named.startswith('openai called this tool: stackademy_api({"course": "CS210"})'), named)
        self.assertIn(f'"name": "{function_name}"', named)
        self.assertTrue(unnamed.startswith(f"openai called this tool: {function_name}("), unnamed)

    def test_process_tool_call_names_a_plugin_by_its_name(self):
        """Process_tool_call() passes the plugin's name, not its function name, to the tool call's message."""
        plugin_meta = MagicMock()
        plugin_meta.name = "stackademy_api"
        with patch.object(module.PluginMeta, "get_cached_object", return_value=plugin_meta):
            # refused by a budget, so that the plugin isn't called.
            self.process(f"{PLUGIN_PREFIX}_0000000022", refusal="over budget")
        # process() replaced append_message_tool_called with a mock.
        OpenAISmarterClient.append_message_tool_called.assert_called_once()  # type: ignore[attr-defined]
        kwargs = OpenAISmarterClient.append_message_tool_called.call_args.kwargs  # type: ignore[attr-defined]
        self.assertEqual(kwargs["tool_name"], "stackademy_api")

    def test_tool_definition_must_be_a_dict(self):
        with self.assertRaises(SmarterValueError):
            self.prep_first_request([{"type": "function", "function": "not a dict"}])

    # -------------------------------------------------------------------------
    # guards
    # -------------------------------------------------------------------------
    def test_responses_need_a_chat_completion_message(self):
        response = MagicMock()
        response.choices[0].message.model_dump_json.return_value = "{}"
        response.model_dump_json.return_value = "{}"
        with self.assertRaises(SmarterConfigurationError):
            self.client.append_openai_response(response)
        with self.assertRaises(SmarterConfigurationError):
            self.client.append_openai_error_response(response, e=ValueError("bad"))

    def test_handle_completion_needs_a_response(self):
        self.client.second_iteration = None
        with self.assertRaises(SmarterValueError):
            self.client.handle_completion()
        self.client.second_iteration = {}
        self.client.first_iteration = {}
        with self.assertRaises(SmarterValueError):
            self.client.handle_completion()

    def test_handle_plugin_selected_guards(self):
        plugin = MagicMock()
        with patch.object(OpenAISmarterClient, "messages", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SmarterValueError):
                self.client.handle_plugin_selected(plugin)
        with self.assertRaises(SmarterValueError):
            self.client.handle_plugin_selected(plugin)

    # -------------------------------------------------------------------------
    # process_tool_call
    # -------------------------------------------------------------------------
    def tool_call(self, name: str, arguments: str = "{}") -> ChatCompletionMessageToolCall:
        return ChatCompletionMessageToolCall(
            id="call_1", type="function", function=Function(name=name, arguments=arguments)
        )

    def process(self, name: str, function=None, refusal=None, **properties):
        """Process a tool call of ``name``, with the client's tool-call bookkeeping replaced."""
        self.client.available_functions = {name: function or MagicMock()}
        self.client.serialized_tool_calls = []
        patchers = [
            patch.object(OpenAISmarterClient, "append_message_tool_called"),
            patch.object(OpenAISmarterClient, "handle_tool_called"),
            patch.object(OpenAISmarterClient, "tool_budget_refusal", return_value=refusal),
        ]
        patchers += [
            patch.object(OpenAISmarterClient, key, new_callable=PropertyMock, return_value=value)
            for key, value in properties.items()
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client.process_tool_call(self.tool_call(name))

    def extension_toolkit(self, result) -> MagicMock:
        """Give the client an extension toolkit whose one tool, ext_calculator_calculator, returns ``result``."""
        toolkit = MagicMock()
        toolkit.is_extension_function.side_effect = lambda name: name == "ext_calculator_calculator"
        toolkit.call.return_value = result
        toolkit.extension_for.return_value = MagicMock(
            pk=3, slug="calculator", installed_version=MagicMock(version="1.0.0")
        )
        toolkit.tool_name_for.return_value = "calculator"
        self.client.extension_toolkit = toolkit
        self.addCleanup(setattr, self.client, "extension_toolkit", None)
        return toolkit

    def test_extension_tool_call_with_a_json_response(self):
        """An extension tool's result is returned to the LLM as JSON, and its extension is recorded."""
        self.extension_toolkit({"result": 2})
        self.process("ext_calculator_calculator")
        serialized = self.client.serialized_tool_calls[0]
        self.assertEqual(serialized["function_name"], "ext_calculator_calculator")
        self.assertEqual(
            serialized["smarter_extension"], {"id": 3, "slug": "calculator", "version": "1.0.0", "tool": "calculator"}
        )
        self.assertEqual(self.append_message.call_args.kwargs["content"], json.dumps({"result": 2}))

    def test_tool_call_refused_by_a_budget(self):
        function = MagicMock()
        self.process("calculator", function=function, refusal="over budget")
        function.assert_not_called()
        self.assertEqual(self.append_message.call_args.kwargs["content"], "over budget")

    def test_tool_signals_carry_the_tool_display_name(self):
        """The tool signals of a tool call carry its display name, for progress messages."""
        with (
            patch.object(OpenAISmarterClient, "tool_display_name", return_value="Calculator") as display_name,
            patch.object(module.llm_tool_requested, "send") as requested,
            patch.object(module.llm_tool_responded, "send") as responded,
        ):
            self.extension_toolkit("2")
            self.process("ext_calculator_calculator")
        display_name.assert_called_once_with("ext_calculator_calculator")
        self.assertEqual(requested.call_args.kwargs["tool_name"], "Calculator")
        self.assertEqual(responded.call_args.kwargs["tool_name"], "Calculator")

    def test_unrecognized_function(self):
        with self.assertRaises(SmarterConfigurationError):
            self.process("not_a_function")

    def test_plugin_tool_call_guards(self):
        """A plugin tool call needs the plugin, an account and a user profile."""
        with self.assertRaises(SmarterConfigurationError):
            self.process(f"{PLUGIN_PREFIX}_2147483646")
        with patch.object(module.PluginMeta, "get_cached_object", return_value=MagicMock()):
            for properties in (
                {"account": None},
                {"account": MagicMock(), "user_profile": None},
                {"account": MagicMock(), "user_profile": MagicMock()},
            ):
                with self.subTest(properties=list(properties)):
                    with self.assertRaises(SmarterConfigurationError):
                        self.process(f"{PLUGIN_PREFIX}_1", **properties)


class TestChatProviderBaseUnits(SmarterTestBase):
    """Test ChatProviderBase's validation and request helpers, on a client without its handler state."""

    def setUp(self):
        super().setUp()
        self.client = OpenAISmarterClient.__new__(OpenAISmarterClient)
        self.client._default_model = None

    def patch_properties(self, **values) -> None:
        for name, value in values.items():
            patcher = patch.object(OpenAISmarterClient, name, new_callable=PropertyMock, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_prune_empty_values(self):
        self.assertEqual(
            self.client.prune_empty_values({"a": None, "b": {"c": None, "d": 1}, "e": [1, None]}),
            {"b": {"d": 1}, "e": [1]},
        )
        with self.assertRaises(SmarterValueError):
            self.client.prune_empty_values(["not", "a", "dict"])  # type: ignore[arg-type]

    def test_validate_requires_each_property(self):
        """Validate() names the first missing property, then rejects a model that isn't valid."""
        required = {
            "prompt": MagicMock(),
            "data": {"messages": []},
            "user": MagicMock(),
            "default_model": "gpt-test",
            "default_system_role": "You are a test.",
            "default_temperature": 0.5,
            "default_max_tokens": 100,
        }
        for missing in required:
            with self.subTest(missing=missing):
                values = {**required, missing: None}
                with patch.multiple(
                    OpenAISmarterClient,
                    **{name: PropertyMock(return_value=value) for name, value in values.items()},
                ):
                    with self.assertRaises(SmarterValueError):
                        self.client.validate()
        with patch.multiple(
            OpenAISmarterClient,
            valid_chat_completion_models=PropertyMock(return_value=["another-model"]),
            provider_name=PropertyMock(return_value="test-provider"),
            api_key=PropertyMock(return_value="sk-test"),
            **{name: PropertyMock(return_value=value) for name, value in required.items()},
        ):
            with self.assertRaises(SmarterValueError):
                self.client.validate()

    def test_validate_requires_an_api_key(self):
        """A Provider without an API key, e.g. a built-in one whose key is not set, fails with how to set it."""
        required = {
            "prompt": MagicMock(),
            "data": {"messages": []},
            "user": MagicMock(),
            "default_model": "gpt-test",
            "default_system_role": "You are a test.",
            "default_temperature": 0.5,
            "default_max_tokens": 100,
        }
        for provider_name, env_var, api_key in (
            ("openai", "OPENAI_API_KEY", None),
            ("googleai", "GEMINI_API_KEY", ""),
            ("custom", "CUSTOM_API_KEY", "SET-ME-PLEASE"),
        ):
            with (
                self.subTest(provider=provider_name),
                patch.multiple(
                    OpenAISmarterClient,
                    provider_name=PropertyMock(return_value=provider_name),
                    api_key=PropertyMock(return_value=api_key),
                    **{name: PropertyMock(return_value=value) for name, value in required.items()},
                ),
                patch.object(base_module, "base_logger") as logger,
            ):
                with self.assertRaises(SmarterConfigurationError) as context:
                    self.client.validate()
                self.assertIn(f"SMARTER_{env_var}", str(context.exception))
                self.assertIn("initialize_providers", str(context.exception))
                self.assertIn(f"SMARTER_{env_var}=<your key>", logger.error.call_args.args[0])

    def test_default_model_from_the_provider(self):
        self.patch_properties(provider=MagicMock(default_model="provider-model"))
        self.assertEqual(self.client.default_model, "provider-model")
        patch.stopall()
        self.patch_properties(provider=None)
        self.assertIsNone(self.client.default_model)

    def test_get_input_text_prompt_errors(self):
        for input_text in ("", 5):
            with (
                self.subTest(input_text=input_text),
                patch(
                    "smarter.apps.provider.services.text_completion.lib.chat_provider_base.parse_request",
                    return_value=(None, input_text),
                ),
            ):
                with self.assertRaises(SmarterValueError):
                    self.client.get_input_text_prompt({"input_text": "x"})

    def test_get_message_thread_adds_the_date_time_once(self):
        """A message thread without a system prompt gets the LLMClient's system role, with one date/time line."""
        llmclient = MagicMock(default_system_role="You are a test.")
        llmclient.default_system_role_enhanced = f"{base_module.get_date_time_string()}You are a test."
        for prompt, expected in (
            (MagicMock(llmclient=llmclient), "You are a test."),
            (MagicMock(llmclient=None), ""),
        ):
            with self.subTest(expected=expected):
                patch.stopall()
                self.patch_properties(prompt=prompt)
                messages = self.client.get_message_thread({"messages": [{"role": "user", "content": "hi"}]})
                system_role = messages[0]["content"]
                self.assertEqual(messages[0]["role"], "system")
                self.assertEqual(system_role.count("The current date/time is"), 1)
                self.assertTrue(system_role.endswith(expected))
