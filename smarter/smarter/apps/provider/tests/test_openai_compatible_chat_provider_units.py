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
        """Built-in functions and plugins that can't be found are never refused."""
        self.assertIsNone(self.client.tool_budget_refusal("get_current_weather"))
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

    def test_handle_response_needs_a_response_with_usage(self):
        """Handle_response needs a response, and the response needs usage."""
        self.client.iteration = 1
        self.client.first_response = None
        with self.assertRaises(SmarterValueError):
            self.client.handle_response()
        self.client.first_response = chat_completion("hi")
        with self.assertRaises(SmarterValueError):
            self.client.handle_response()

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

    def test_tool_definition_must_be_a_dict(self):
        with self.assertRaises(SmarterValueError):
            self.prep_first_request([{"type": "function", "function": "not a dict"}])

    # -------------------------------------------------------------------------
    # handle_function_provided
    # -------------------------------------------------------------------------
    def test_builtin_functions_are_provided(self):
        for function in ("get_current_weather", "date_calculator", "calculator", "not_a_builtin"):
            self.client.handle_function_provided(function)
        self.assertEqual(
            sorted(self.client.available_functions), ["calculator", "date_calculator", "get_current_weather"]
        )
        self.assertEqual(len(self.client.tools), 3)

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

    def test_builtin_tool_call_with_a_json_response(self):
        self.process("calculator", function=MagicMock(return_value={"result": 2}))
        self.assertEqual(self.client.serialized_tool_calls[0]["function_name"], "calculator")
        self.assertEqual(self.append_message.call_args.kwargs["content"], json.dumps({"result": 2}))

    def test_tool_call_refused_by_a_budget(self):
        function = MagicMock()
        self.process("calculator", function=function, refusal="over budget")
        function.assert_not_called()
        self.assertEqual(self.append_message.call_args.kwargs["content"], "over budget")

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
            **{name: PropertyMock(return_value=value) for name, value in required.items()},
        ):
            with self.assertRaises(SmarterValueError):
                self.client.validate()

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
