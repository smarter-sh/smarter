# pylint: disable=W0602,C0302
"""Base class for prompt providers."""

import ast
import re
import time
import traceback
from http import HTTPStatus
from typing import Any, Optional, Union

import openai
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallUnion,
)
from openai.types.completion_usage import CompletionUsage

from smarter.apps.account.models import (
    ChargeTypes,
    SmarterBudgetExceeded,
    UserProfile,
    charge_authorization,
)
from smarter.apps.guardrail.services import (
    GuardrailBlockedError,
    GuardrailPipeline,
    GuardrailStage,
    PipelineDisposition,
)
from smarter.apps.mcpclient.toolkit import MCPToolkit
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginMeta, PluginPrompt
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.apps.prompt.functions.calculator import (
    calculator,
    calculator_tool_factory,
)
from smarter.apps.prompt.functions.date_calculator import (
    date_calculator,
    date_calculator_tool_factory,
)
from smarter.apps.prompt.functions.function_weather import (
    get_current_weather,
    weather_tool_factory,
)
from smarter.apps.prompt.models import Prompt
from smarter.apps.prompt.receivers import (
    llm_tool_presented,
    llm_tool_requested,
    llm_tool_responded,
)
from smarter.apps.prompt.signals import (
    chat_plugin_called,
    chat_request,
    chat_response,
    chat_response_failure,
    chat_tool_called,
    prompt_finished,
    prompt_started,
)
from smarter.apps.provider.services.text_completion.const import OpenAIMessageKeys
from smarter.apps.provider.services.text_completion.lib.protocols import (
    SmarterChatCompletionResponseType,
)
from smarter.apps.provider.services.text_completion.utils import (
    http_response_factory,
    pair_tool_messages,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import (
    SmarterConfigurationError,
    SmarterIlligalInvocationError,
    SmarterValueError,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json, logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .chat_provider_base import SmarterChatProviderBase
from .exception_map import exception_status_and_message
from .internal_keys import _InternalKeys


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


OPENAI_TOOL_CHOICE = "auto"
REASONING_EFFORT_NONE = "none"

TOOLS_REQUIRE_NO_REASONING_MODELS: set[str] = {"gpt-6-luna"}
"""
Models whose v1/chat/completions endpoint rejects function tools unless reasoning_effort is 'none'.

OpenAI returns a 400 for these models when a request has tools and omits reasoning_effort, because
their default effort is not 'none'. The set is not exhaustive: a model that fails this way at runtime
is added to it, so each process pays for the failed request at most once per model. reasoning_effort
is never sent otherwise, because older models such as gpt-4o-mini, and some OpenAI-compatible
providers, reject the parameter.
"""

base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


BLOCKED_MESSAGE_PLACEHOLDER = "[This message was blocked by a guardrail.]"
"""What replaces a user message that an input guardrail blocked, in the conversation's history."""

MARKDOWN_SYSTEM_PROMPT = (
    "Your responses are displayed in a chat window that renders GitHub flavored Markdown: headings, bold, "
    "italics, strikethrough, lists, tables, block quotes, inline code, fenced code blocks, links and images. "
    "Use Markdown when it makes a response clearer, and name the language of each fenced code block. "
    "The chat window does not render HTML, LaTeX or Mermaid, so do not use them. "
    "To show an image, use Markdown image syntax, ![description](https://...), but only with an image url "
    "that the user gave you or that a tool returned. NEVER invent an image url, because a broken image "
    "looks worse than no image."
)
"""
Added to the system prompt of every request, so that the LLM knows what the chat window renders.

It is the single source of the chat window's rendering rules, so an LLMClient's ``defaultSystemRole``
need not repeat them, and should only describe the formatting that suits its own persona.

It is added to the request's messages only (see :attr:`OpenAISmarterClient.openai_messages`), and is
never saved in the conversation's history, nor displayed in the chat.
"""


class OpenAISmarterClient(SmarterChatProviderBase):
    """
    Prompt provider for OpenAI-compatible text completion APIs.

    This provider class enables seamless integration with any vendor or service
    that implements the OpenAI prompt completion API, including both OpenAI and third-party providers
    that adhere to the same protocol and message formats.

    **Key Features:**

        - Supports OpenAI's prompt completion API and compatible alternatives.
        - Handles message formatting, tool calls, plugin integration, and billing.
        - Manages multi-step prompt completion workflows, including tool and plugin responses.
        - Provides hooks for plugin selection, function registration, and error handling.

    **Usage:**

        Inherit from this class to implement a prompt provider that communicates with any OpenAI-compatible API endpoint.
        This class is suitable for use cases where you want to support multiple LLM vendors with a unified interface.

    **Example:**

        .. code-block:: python

            class MyProvider(OpenAISmarterClient):
                pass

            provider = MyProvider()
            response = provider.handler(user_profile, prompt, data)

    .. seealso::
        - https://developers.openai.com/api/reference/overview/prompt
        - :class:`SmarterChatProviderBase`
    """

    mcp_toolkit: Optional[MCPToolkit] = None
    """The MCP tools of the current prompt.

    See :meth:`handle_mcp_clients`.
    """

    guardrail_pipeline: Optional[GuardrailPipeline] = None
    """The MCP tools of the current prompt.

    See :meth:`handle_mcp_clients`.
    """

    @property
    def openai_messages(self) -> list[dict[str, Any]]:
        """
        Return a sanitized list of messages compatible with OpenAI's prompt completion API.

        This property processes the internal message list, removing Smarter-specific annotations
        (such as metadata about tool calls and interim completion token charges) to ensure that
        only valid OpenAI message fields are included. This is essential for avoiding API errors
        related to unexpected or extraneous fields.

        :returns: A list of dictionaries representing prompt messages, formatted for OpenAI's API.
        :rtype: list[dict[str, Any]]

        :raises SmarterValueError: If the internal message list is not a list.

        Example::

            [
                {
                    "role": "assistant",
                    "content": "Welcome to Smarter!",
                    "tool_calls": [
                        {
                            "id": "call_ABC123",
                            "type": "function",
                            "function": {
                                "name": "smarter_plugin_0000000045",
                                "arguments": "{\"description\":\"AI\"}"
                            }
                        }
                    ]
                },
                {
                    "role": "tool",
                    "name": "smarter_plugin_0000000045",
                    "content": "SqlPlugin stackademy_sql response: ...",
                    "tool_call_id": "call_ABC123"
                }
            ]

        .. important::

            - OpenAI expects that every assistant message with a ``tool_calls`` field is immediately followed by a corresponding ``tool`` message for each ``tool_call_id``. Failure to do so will result in an API error.

            - If you include Smarter-specific fields (such as ``smarter_is_new``) in the message list, OpenAI's API may reject the request.

            - On the first iteration, tool call responses are excluded from the message list to comply with OpenAI's requirements.

        .. seealso::

            - https://developers.openai.com/api/reference/overview/prompt/create
            - :class:`OpenAIMessageKeys`
        """
        if not isinstance(self.messages, list):
            raise SmarterValueError(f"{self.formatted_class_name}: messages must be a list, got {type(self.messages)}")

        if self.iteration == 1:
            # ensure that we're not passing any tool call responses to the first request.
            # mcdaniel 2025-09-26: this was causing issues with OpenAI's API.
            filtered_messages = [
                message
                for message in self.messages
                if message[OpenAIMessageKeys.MESSAGE_ROLE_KEY] in OpenAIMessageKeys.all
            ]
        else:
            filtered_messages = [
                message
                for message in self.messages
                if message[OpenAIMessageKeys.MESSAGE_ROLE_KEY] in OpenAIMessageKeys.all
            ]

        retval = []
        for message in filtered_messages:
            message_copy = message.copy()
            if _InternalKeys.SMARTER_IS_NEW in message_copy:
                del message_copy[_InternalKeys.SMARTER_IS_NEW]
            retval.append(message_copy)
        retval = self.add_markdown_system_prompt(retval)
        # the thread may come from the client, which keeps the tool replies but not the
        # assistant's tool_calls, and OpenAI refuses a tool reply without its tool call.
        return pair_tool_messages(retval)

    @staticmethod
    def add_markdown_system_prompt(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Tell the LLM that its responses may use Markdown.

        :data:`MARKDOWN_SYSTEM_PROMPT` is appended to the first system message, or is the system
        message of a thread that has none. The messages are copies, so the conversation's history
        is unchanged.

        :param messages: The request's messages.
        :type messages: list[dict[str, Any]]

        :returns: The request's messages, with the Markdown instructions.
        :rtype: list[dict[str, Any]]
        """
        for i, message in enumerate(messages):
            if message.get(OpenAIMessageKeys.MESSAGE_ROLE_KEY) == OpenAIMessageKeys.SYSTEM_MESSAGE_KEY:
                content = message.get(OpenAIMessageKeys.MESSAGE_CONTENT_KEY) or ""
                if MARKDOWN_SYSTEM_PROMPT not in content:
                    messages[i] = {
                        **message,
                        OpenAIMessageKeys.MESSAGE_CONTENT_KEY: f"{content}\n\n{MARKDOWN_SYSTEM_PROMPT}".strip(),
                    }
                return messages
        return [
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: MARKDOWN_SYSTEM_PROMPT,
            },
            *messages,
        ]

    @property
    def new_messages(self) -> list[dict[str, Any]]:
        """
        Return a list of messages that are marked as new.

        This property filters the internal message list to return only those messages
        that have the 'smarter_is_new' flag set to True.

        :returns: A list of new messages.
        :rtype: list[dict[str, Any]]
        """
        if self.messages is None:
            return []

        try:
            return [message for message in self.messages if message[_InternalKeys.SMARTER_IS_NEW]]
        except KeyError:
            prefix = formatted_text(f"{self.formatted_class_name} new_messages()")
            logger.error(
                "%s - KeyError: '%s' key not found in message: %s", prefix, _InternalKeys.SMARTER_IS_NEW, self.messages
            )
        return self.messages

    def prep_first_request(self):
        """
        Prepare the first request for the prompt completion.

        This is called
        at the beginning of the prompt completion process.

        :raises SmarterValueError: If the messages are not a list, or if tool definitions are invalid.

        :returns: None
        :rtype: None
        """
        logger.debug("%s.prep_first_request()", self.formatted_class_name)
        # ensure that all message history is marked as not new
        if isinstance(self.messages, list):
            self.messages = self.messages_set_is_new(self.messages, is_new=False)
        tool_choice = OPENAI_TOOL_CHOICE
        self.first_iteration[_InternalKeys.REQUEST_KEY] = {
            _InternalKeys.API_URL: self.base_url,
            _InternalKeys.API_KEY: self.mask_string(self.api_key),
            _InternalKeys.MODEL_KEY: self.model,
            _InternalKeys.MESSAGES_KEY: self.openai_messages,
            _InternalKeys.TEMPERATURE_KEY: self.temperature,
            _InternalKeys.MAX_COMPLETION_TOKENS_KEY: self.max_completion_tokens,
            _InternalKeys.TOOLS_KEY: self.tools,
        }

        # create a Smarter UI message with the established configuration
        content = f"Prompt configuration: llm={self.provider_name}, url={self.url} api_key={self.mask_string(self.api_key)} model={self.model}, temperature={self.temperature}, max_completion_tokens={self.max_completion_tokens}"
        if self.tools:
            content = content + f", tool_choice={tool_choice}."
        self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

        if self.tools:
            # this is necessary because of this 400 response in cases where
            # tool_choice is set but not tools are provided:
            # 'Error code: 400 - Invalid value 'tool_choice' is only allowed when 'tools' are specified."
            #
            # pylint: disable=E1137
            self.first_iteration[_InternalKeys.REQUEST_KEY][_InternalKeys.TOOL_CHOICE] = tool_choice

            # for any tools that are included in the request, add Smarter UI messages for each tool
            for tool in self.tools:
                tool_type = tool.get("type")
                if not tool_type:
                    logger.warning(
                        "%s: tool type is required in tool definition: %s. This is a bug",
                        self.formatted_class_name,
                        tool,
                    )
                this_tool = tool.get(tool_type) if tool_type else {}
                if not isinstance(this_tool, dict):
                    raise SmarterValueError(
                        f"{self.formatted_class_name}: tool definition for tool type '{tool_type}' must be a dictionary. Got {type(this_tool)}. Tool definition: {tool}"
                    )
                tool_name = this_tool.get("name")
                if not tool_name:
                    logger.warning(
                        "%s: tool name is required in tool definition: %s. This is a bug",
                        self.formatted_class_name,
                        tool,
                    )
                tool_description = this_tool.get("description")
                if not tool_description:
                    logger.warning(
                        "%s: tool description is required in tool definition: %s. This is a bug",
                        self.formatted_class_name,
                        tool,
                    )
                tool_parameters = this_tool.get("parameters", {}).get("properties", {})
                inputs = []
                for parameter, details in tool_parameters.items():
                    if "description" in details:
                        inputs.append(f"{parameter}: {details['description']}")
                    elif "enum" in details:
                        inputs.append(f"{parameter}: {', '.join(details['enum'])}")

                inputs = ", ".join(inputs)
                content = f"Tool presented: {tool_name}({inputs}) - {tool_description} "
                content = content + f"\n\nTool definition:\n--------------------\n{json.dumps(tool, indent=4)}"
                self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

        # send a prompt completion request signal. this triggers a variety of db records to be created
        # asynchronously in the background via Celery tasks.
        chat_request.send(
            sender=self.handler,
            prompt=self.prompt,
            iteration=self.iteration,
            data=self.first_iteration[_InternalKeys.REQUEST_KEY],
        )

    def prep_second_request(self):
        """
        Prepare the second request for the prompt completion.

        This is called
        in response to a tool call that requires a second request to the LLM.

        :returns: None
        :rtype: None
        """
        logger.debug("%s.prep_second_request() called.", self.formatted_class_name)
        if not isinstance(self.second_iteration, dict):
            raise SmarterValueError(
                f"{self.formatted_class_name}: second_iteration must be a dictionary, got {type(self.second_iteration)}"
            )
        self.second_iteration[_InternalKeys.REQUEST_KEY] = {
            _InternalKeys.API_URL: self.base_url,
            _InternalKeys.API_KEY: self.mask_string(self.api_key),
            _InternalKeys.MODEL_KEY: self.model,
            _InternalKeys.MESSAGES_KEY: self.openai_messages,
        }
        chat_request.send(
            sender=self.handler,
            prompt=self.prompt,
            iteration=self.iteration,
            data=self.second_iteration[_InternalKeys.REQUEST_KEY],
        )

    def append_openai_response(self, response: ChatCompletion) -> None:
        """
        Append the OpenAI-compatible response message to the internal message list.

        2025-06-20: updated to use model_dump_json() to ensure compatibility with Pydantic v2.
        2025-10-02: updated to validate that the response message is indeed a ChatCompletionMessage.

        :param response: The OpenAI-compatible prompt completion response.
        :type response: ChatCompletion

        :returns: None
        :rtype: None
        """
        logger.debug("%s.append_openai_response() called.", self.formatted_class_name)
        response_message = response.choices[0].message
        message_json = json.loads(response_message.model_dump_json())
        if not isinstance(response_message, ChatCompletionMessage):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}: response_message is not of the expected type ChatCompletionMessage. Received response of type {type(response_message)}. Response: {response.model_dump_json()}"
            )
        self.append_message(role=response_message.role, content=response_message.content, message=message_json)  # type: ignore[call-arg]

    def append_openai_error_response(self, response: ChatCompletion, e: Optional[Exception] = None) -> None:
        """
        Append an error message to the internal message list based on the OpenAI response.

        :param response: The OpenAI prompt completion response containing the error.
        :type response: ChatCompletion

        :returns: None
        :rtype: None
        """

        def extract_json_objects(text) -> Optional[dict[str, Any]]:
            """
            Evaluate the text to attempt to extract any JSON objects that may be present.

            This is useful for extracting json error information that might exist inside of the error messages.

            Find all curly-brace blocks (non-greedy) and attempt to parse
            them as JSON objects.

            example: a string like this:

                'Error code: 404 - {
                    'error': {
                        'message': 'The model `gpt-not-a-valid-model` does not exist or you do not have access to it.',
                        'type': 'invalid_request_error',
                        'param': None,
                        'code': 'model_not_found'
                    }
                }'
            """

            candidates = re.findall(r"{.*}", text, re.DOTALL)
            for candidate in candidates:
                try:
                    logger.debug(
                        "%s.extract_json_objects() trying ast to parse candidate: %s",
                        self.formatted_class_name,
                        candidate,
                    )
                    obj = ast.literal_eval(candidate)
                    json.dumps(obj)  # validate the json
                    return obj
                # pylint: disable=broad-except
                except Exception:
                    logger.debug(
                        "%s.extract_json_objects() ast failed to parse candidate: %s",
                        self.formatted_class_name,
                        candidate,
                    )
                    continue

        logger.debug("%s.append_openai_error_response() called.", self.formatted_class_name)
        response_message = response.choices[0].message
        if not isinstance(response_message, ChatCompletionMessage):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}: response_message is not of the expected type ChatCompletionMessage. Received response of type {type(response_message)}. Response: {response.model_dump_json()}"
            )
        content = str(response_message.content)
        json_objects = extract_json_objects(content)
        if json_objects:
            # create a more nicely formatted message.
            content = f"{self.base_url} raised the following {e.__class__.__name__} exception: {json.dumps(json_objects, indent=4)}"

        stack_trace = traceback.format_exc()
        content = content + f"\n\nPython Stack trace:\n--------------------\n{stack_trace}"

        self.append_message(role=OpenAIMessageKeys.SMARTER_ERROR_KEY, content=content)

    def handle_response(self) -> None:
        """
        Handle internal billing, and append messages to the response for prompt completion and the billing summary.

        :returns: None
        :rtype: None
        """
        logger.debug("%s.handle_response() iteration: %s", self.formatted_class_name, self.iteration)

        response = self.second_response if self.iteration == 2 else self.first_response
        if not response:
            raise SmarterValueError(
                f"{self.formatted_class_name}.handle_response(): response is required for iteration {self.iteration}, but was not set."
            )
        if not response.usage:
            raise SmarterValueError(
                f"{self.formatted_class_name}.handle_response(): response.usage is required for iteration {self.iteration}, but was not set."
            )
        self.prompt_tokens = response.usage.prompt_tokens
        self.completion_tokens = response.usage.completion_tokens
        self.total_tokens = response.usage.total_tokens
        self.reference = response.system_fingerprint

        resource_locators = [self.provider.record_locator, self.prompt.llmclient.record_locator]  # type: ignore[assignment]
        self._insert_charge_by_type(resource_locators, ChargeTypes.PROMPT_COMPLETION.value)
        self.append_message(
            role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY,
            content=f"{self.provider_name} prompt charges: {self.prompt_tokens} prompt tokens, {self.completion_tokens} completion tokens = {self.total_tokens} total tokens charged.",
        )

        if self.iteration == 1:
            if not self.first_response:
                raise SmarterIlligalInvocationError(
                    f"{self.formatted_class_name}.handle_response(): first_response is required for iteration 1, but was not set."
                )
            self.first_iteration[_InternalKeys.RESPONSE_KEY] = json.loads(self.first_response.model_dump_json())
        if self.iteration == 2:
            if not self.second_response:
                raise SmarterIlligalInvocationError(
                    f"{self.formatted_class_name}.handle_response(): second_response is required for iteration 2, but was not set."
                )
            if not isinstance(self.second_iteration, dict):
                raise SmarterValueError(
                    f"{self.formatted_class_name}.handle_response(): second_iteration must be a dictionary, got {type(self.second_iteration)}"
                )
            self.second_iteration[_InternalKeys.RESPONSE_KEY] = json.loads(self.second_response.model_dump_json())

        serialized_request = (
            self.first_iteration[_InternalKeys.REQUEST_KEY]
            if self.iteration == 1
            else self.second_iteration[_InternalKeys.REQUEST_KEY] if self.second_iteration else None
        )
        serialized_response = (
            self.first_iteration[_InternalKeys.RESPONSE_KEY]
            if self.iteration == 1
            else self.second_iteration[_InternalKeys.RESPONSE_KEY] if self.second_iteration else None
        )

        chat_response.send(
            sender=self.handler,
            prompt=self.prompt,
            iteration=self.iteration,
            request=serialized_request,
            response=serialized_response,
            messages=self.messages,
        )

    def handle_tool_called(
        self, function_name: str, function_args: str, extra_resource_locators: Optional[list[str]] = None
    ) -> None:
        """
        Handle a built-in tool call.

        example: get_current_weather()

        :param function_name: The name of the tool function called.
        :type function_name: str
        :param function_args: The arguments passed to the tool function.
        :type function_args: str
        :param extra_resource_locators: The record locators of any other resources that the tool
            call used, e.g. an MCPClient, to include in the charge.
        :type extra_resource_locators: Optional[list[str]]

        :returns: None
        :rtype: None
        """
        logger.debug("%s.handle_tool_called() - %s", self.formatted_class_name, function_name)
        request = (self.first_iteration[_InternalKeys.REQUEST_KEY],)
        response = (self.first_iteration[_InternalKeys.RESPONSE_KEY],)
        chat_tool_called.send(
            sender=self.handler,
            prompt=self.prompt,
            plugin=None,
            function_name=function_name,
            function_args=function_args,
            request=request,
            response=response,
        )
        resource_locators = [self.provider.record_locator]  # type: ignore[assignment]
        if isinstance(self.prompt, Prompt) and self.prompt.llmclient:
            resource_locators.append(self.prompt.llmclient.record_locator)
        resource_locators.extend(extra_resource_locators or [])
        self._insert_charge_by_type(resource_locators, ChargeTypes.TOOL.value)
        self.db_insert_chat_tool_call(
            function_name=function_name, function_args=function_args, request=request, response=response
        )

    def handle_plugin_called(self, plugin: PluginBase) -> None:
        """
        Handle a plugin tool call.

        example: SqlPlugin, ApiPlugin, StaticPlugin etc.

        :param plugin: The plugin instance that was called.
        :type plugin: PluginBase

        :returns: None
        :rtype: None
        """
        logger.debug("%s.handle_plugin_called() - %s", self.formatted_class_name, plugin.name)
        chat_plugin_called.send(
            sender=self.handler,
            prompt=self.prompt,
            plugin=plugin,
            input_text=self.input_text,
        )
        resource_locators = [self.provider.record_locator]  # type: ignore[assignment]
        resource_locators.append(self.prompt.llmclient.record_locator)  # type: ignore[union-attr]
        resource_locators.append(plugin.plugin_meta.record_locator)  # type: ignore[union-attr]
        if plugin.plugin_data and hasattr(plugin.plugin_data, "connection"):
            resource_locators.append(plugin.plugin_data.connection.record_locator)  # type: ignore[union-attr]

        self._insert_charge_by_type(resource_locators, ChargeTypes.PLUGIN.value)
        self.db_insert_chat_plugin_usage(prompt=self.prompt, plugin=plugin, input_text=self.input_text)

    def process_tool_call(self, tool_call: ChatCompletionMessageToolCallUnion):
        """
        Process a tool call from the LLM.

        This method handles both built-in tool calls
        and plugin tool calls.

        :param tool_call: The tool call data from the LLM.
        :type tool_call: ChatCompletionMessageToolCallUnion

        :returns: None
        :rtype: None
        """
        logger.debug("%s.process_tool_call() called", self.formatted_class_name)
        if not isinstance(tool_call, ChatCompletionMessageToolCall):
            raise SmarterValueError(
                f"{self.formatted_class_name}: tool_call must be a ChatCompletionMessageToolCall, got {type(tool_call)}. This is a bug."
            )
        llm_tool_requested.send(sender=self.process_tool_call, tool_call=tool_call.model_dump())
        if not tool_call:
            raise SmarterValueError(f"{self.formatted_class_name}: tool_call is required")
        serialized_tool_call = {}
        plugin: Optional[PluginBase] = None
        function_name = tool_call.function.name
        try:
            function_to_call = self.available_functions[function_name]
        except KeyError as e:
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}: function '{function_name}' not found in available functions: {self.available_functions}"
            ) from e

        function_args = json.loads(tool_call.function.arguments)
        serialized_tool_call["function_name"] = function_name
        serialized_tool_call["function_args"] = function_args
        self.append_message_tool_called(tool_call=tool_call)

        function_response = None
        extra_resource_locators: list[str] = []
        budget_refusal = self.tool_budget_refusal(function_name)
        if budget_refusal is not None:
            # a budget forbids charges to the plugin or MCP server, so the LLM is told why instead.
            function_response = budget_refusal
        elif function_name in [get_current_weather.__name__, date_calculator.__name__, calculator.__name__]:
            function_response = function_to_call(tool_call=tool_call)

        elif self.mcp_toolkit is not None and self.mcp_toolkit.is_mcp_function(function_name):
            mcpclient = self.mcp_toolkit.mcpclient_for(function_name)
            function_response = self.mcp_toolkit.call(function_name, function_args)
            if mcpclient is not None:
                serialized_tool_call[_InternalKeys.SMARTER_MCPCLIENT_KEY] = {
                    "id": mcpclient.id,  # type: ignore[attr-defined]
                    "name": mcpclient.name,
                    "tool": self.mcp_toolkit.functions[function_name].tool_name,
                }
                extra_resource_locators.append(mcpclient.record_locator)

        elif function_name.startswith(smarter_settings.function_calling_identifier_prefix):
            plugin_id = int(function_name.rsplit("_", 1)[-1])
            try:
                plugin_meta = PluginMeta.get_cached_object(pk=plugin_id)
            except PluginMeta.DoesNotExist as e:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: plugin with id {plugin_id} not found. This is a bug."
                ) from e

            if not self.account:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: account is required to handle plugin calls."
                )
            if not self.user_profile:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: user_profile is required to handle plugin calls."
                )
            if not self.user_profile:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: user_profile is required to handle plugin calls."
                )
            if not isinstance(self.user_profile, UserProfile):
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: user_profile must be an instance of UserProfile, got {type(self.user_profile)}. This is a bug."
                )
            plugin_controller = PluginController(
                user_profile=self.user_profile,
                plugin_meta=plugin_meta,
            )
            if not plugin_controller or not plugin_controller.plugin:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: plugin with id {plugin_id} not found or not initialized."
                )
            plugin = plugin_controller.plugin
            plugin.params = function_args
            function_response = plugin.tool_call_fetch_plugin_response(function_args)
            serialized_tool_call[_InternalKeys.SMARTER_PLUGIN_KEY] = PluginMetaSerializer(plugin.plugin_meta).data
            self.handle_plugin_called(plugin=plugin)
        else:
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}: function '{function_name}' not recognized. Available functions: {self.available_functions}"
            )
        tool_call_message = {
            OpenAIMessageKeys.TOOL_CALL_ID: tool_call.id,
            OpenAIMessageKeys.MESSAGE_NAME_KEY: function_name,
        }
        if isinstance(function_response, (dict, list)):
            function_response = json.dumps(function_response)
        self.append_message(
            role=OpenAIMessageKeys.TOOL_MESSAGE_KEY, content=function_response, message=tool_call_message
        )
        if not isinstance(self.serialized_tool_calls, list):
            raise SmarterValueError(
                f"{self.formatted_class_name}: serialized_tool_calls must be a list, got {type(self.serialized_tool_calls)}"
            )
        self.serialized_tool_calls.append(serialized_tool_call)
        self.handle_tool_called(
            function_name=function_name,
            function_args=function_args,
            extra_resource_locators=extra_resource_locators,
        )
        llm_tool_responded.send(
            sender=self.process_tool_call, tool_call=tool_call.model_dump(), tool_response=function_response
        )

    def authorize_budgets(self) -> None:
        """
        Check the budgets of everything that a prompt completion is charged to, before calling the LLM.

        :raises SmarterBudgetExceeded: if a budget's resource lock forbids charges to the provider,
            the llmclient, the user, or their account.
        """
        resources = [
            getattr(self, "provider", None),
            getattr(self.prompt, "llmclient", None),
            self.user_profile,
            getattr(self.user_profile, "account", None),
        ]
        charge_authorization(
            [resource.record_locator for resource in resources if resource is not None], self.__class__.__name__
        )

    def tool_budget_refusal(self, function_name: str) -> Optional[str]:
        """
        Check the budget of the plugin or MCP server that a tool call would use.

        :returns: The tool response that tells the LLM why the tool cannot be used, or None if it can.
        """
        resource = None
        if self.mcp_toolkit is not None and self.mcp_toolkit.is_mcp_function(function_name):
            resource = self.mcp_toolkit.mcpclient_for(function_name)
        elif function_name.startswith(smarter_settings.function_calling_identifier_prefix):
            try:
                resource = PluginMeta.get_cached_object(pk=int(function_name.rsplit("_", 1)[-1]))
            except (PluginMeta.DoesNotExist, ValueError):
                return None
        if resource is None:
            return None
        try:
            charge_authorization(resource.record_locator, self.__class__.__name__)
        except SmarterBudgetExceeded as e:
            return json.dumps({"error": "budget_exceeded", "message": e.message})
        return None

    def handle_plugin_selected(self, plugin: PluginBase) -> None:
        """
        Handle a plugin being selected.

        does the prompt have anything to do with any of the search terms defined in a plugin?
        The LLMClient's model, temperature and max_completion_tokens are used whichever plugins
        are selected: a plugin customizes the prompt's messages and tools, not the LLM settings.
        2025-10-02: updated to validate that messages and tools are lists.
        2025-10-02: updated to use plugin.plugin_meta.name for the plugin name.

        :param plugin: The plugin instance that was selected.
        :type plugin: PluginBase

        :returns: None
        :rtype: None
        """
        logger.debug("%s.handle_plugin_selected() called.", self.formatted_class_name)
        logger.warning(
            "%s.handle_plugin_selected(): plugins selector needs to be refactored to use Django model.",
            self.formatted_class_name,
        )
        if not isinstance(self.messages, list):
            raise SmarterValueError(f"{self.formatted_class_name}: messages must be a list, got {type(self.messages)}")
        if not isinstance(plugin.plugin_prompt, PluginPrompt):
            raise SmarterValueError(
                f"{self.formatted_class_name}: plugin_prompt must be an instance of PluginPrompt, got {type(plugin.plugin_prompt)}"
            )
        self.messages = plugin.customize_prompt(self.messages)
        if self.tools is None:
            self.tools = []
        self.tools.append(plugin.custom_tool)
        self.available_functions[plugin.function_calling_identifier] = plugin.tool_call_fetch_plugin_response
        self.append_message_plugin_selected(plugin=plugin.plugin_meta.name)  # type: ignore[call-arg]
        llm_tool_presented.send(sender=self.handle_plugin_selected, tool=plugin.custom_tool, plugin=plugin)
        # note to self: Plugin sends a plugin_selected signal, so no need to send it here.

    def append_guardrail_message(self, stage: str, result: Any) -> None:
        """Append a Smarter message that summarizes what the guardrails of a stage did, if anything."""
        triggered = [finding.guardrail_name for finding in result.triggered_findings]
        failed = [outcome.guardrail_name for outcome in result.outcomes if outcome.error]
        if not triggered and not failed:
            return
        content = f"Smarter {stage} guardrails: {result.disposition.value}."
        if triggered:
            content += f" Triggered: {', '.join(sorted(set(triggered)))}."
        if failed:
            content += f" Failed to run: {', '.join(sorted(set(failed)))}."
        self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

    def handle_input_guardrails(self) -> None:
        """
        Run the LLMClient's input guardrails on the user's message.

        The guardrails are those listed in the LLMClient manifest's ``spec.guardrails``. If
        they redact or transform the user's message, the message is replaced, so that the LLM,
        the plugins and the persisted history see the changed message.

        :raises GuardrailBlockedError: If a guardrail blocks the user's message.
        """
        self.guardrail_pipeline = None
        llmclient = self.prompt.llmclient if isinstance(self.prompt, Prompt) else None
        if llmclient is None or not isinstance(self.messages, list):
            return
        pipeline = GuardrailPipeline.for_llmclient(llmclient, session_key=self.prompt.session_key)  # type: ignore[union-attr]
        if not pipeline.guardrails:
            return
        self.guardrail_pipeline = pipeline
        result = pipeline.run_pre({"messages": self.messages})
        if result.disposition in (PipelineDisposition.REDACTED, PipelineDisposition.TRANSFORMED):
            self.messages = result.payload["messages"]
            for message in reversed(self.messages):
                if message.get(OpenAIMessageKeys.MESSAGE_ROLE_KEY) == OpenAIMessageKeys.USER_MESSAGE_KEY:
                    content = message.get(OpenAIMessageKeys.MESSAGE_CONTENT_KEY)
                    if isinstance(content, str):
                        self.input_text = content
                        if isinstance(self.request_meta_data, dict) and "input_text" in self.request_meta_data:
                            self.request_meta_data["input_text"] = content
                    break
        if result.blocked:
            # the blocked message is replaced in the conversation's history, so that it is
            # not sent to the LLM with the history of the conversation's later prompts.
            for message in reversed(self.messages):
                if message.get(OpenAIMessageKeys.MESSAGE_ROLE_KEY) == OpenAIMessageKeys.USER_MESSAGE_KEY:
                    message[OpenAIMessageKeys.MESSAGE_CONTENT_KEY] = BLOCKED_MESSAGE_PLACEHOLDER
                    break
            self.input_text = BLOCKED_MESSAGE_PLACEHOLDER
            if isinstance(self.request_meta_data, dict) and "input_text" in self.request_meta_data:
                self.request_meta_data["input_text"] = BLOCKED_MESSAGE_PLACEHOLDER
        self.append_guardrail_message("input", result)
        if result.blocked:
            raise GuardrailBlockedError(result.fallback_message or "", None)

    def handle_output_guardrails(self, response: ChatCompletion) -> ChatCompletion:
        """
        Run the LLMClient's output guardrails on the LLM's final reply.

        :param response: The LLM's final response.
        :returns: The response, with its reply redacted or transformed, or replaced with the
            guardrail's message if a guardrail blocks it.
        """
        if self.guardrail_pipeline is None or not self.guardrail_pipeline.guardrails_for(GuardrailStage.POST):
            return response
        payload = json.loads(response.model_dump_json())
        result = self.guardrail_pipeline.run_post(payload)
        self.append_guardrail_message("output", result)
        if result.blocked:
            payload["choices"] = payload["choices"][:1]
            message = payload["choices"][0]["message"]
            message.update({"content": result.fallback_message, "refusal": None, "tool_calls": None})
            payload["choices"][0]["finish_reason"] = "content_filter"
            return ChatCompletion.model_validate(payload)
        if result.disposition in (PipelineDisposition.REDACTED, PipelineDisposition.TRANSFORMED):
            return ChatCompletion.model_validate(result.payload)
        return response

    def handle_mcp_clients(self) -> None:
        """
        Offer the LLM the tools of the LLMClient's MCP servers.

        The LLMClient's active MCPClients, listed in its manifest's ``spec.mcpClients``, are
        loaded into an :class:`~smarter.apps.mcpclient.toolkit.MCPToolkit`, whose tools are
        added to the request, and whose servers' instructions are added to the system prompt.
        An MCP server that cannot be reached is skipped, and reported in a Smarter message.

        :returns: None
        :rtype: None
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmclient.models import LLMClientMCPClients

        self.mcp_toolkit = None
        llmclient = self.prompt.llmclient if isinstance(self.prompt, Prompt) else None
        if llmclient is None:
            return
        mcpclients = LLMClientMCPClients.mcpclients_for(llmclient)
        if not mcpclients:
            return
        logger.debug(
            "%s.handle_mcp_clients() loading MCPClients: %s",
            self.formatted_class_name,
            [mcpclient.name for mcpclient in mcpclients],
        )
        self.mcp_toolkit = MCPToolkit(mcpclients).load()
        if self.mcp_toolkit.tools:
            if self.tools is None:
                self.tools = []
            if self.available_functions is None:
                self.available_functions = {}
            self.tools.extend(self.mcp_toolkit.tools)
            for function_name in self.mcp_toolkit.functions:
                self.available_functions[function_name] = self.mcp_toolkit.call
        instructions = self.mcp_toolkit.system_prompt()
        if instructions and isinstance(self.messages, list):
            for i, message in enumerate(self.messages):
                if message.get(OpenAIMessageKeys.MESSAGE_ROLE_KEY) == OpenAIMessageKeys.SYSTEM_MESSAGE_KEY:
                    content = message.get(OpenAIMessageKeys.MESSAGE_CONTENT_KEY) or ""
                    self.messages[i] = {
                        **message,
                        OpenAIMessageKeys.MESSAGE_CONTENT_KEY: f"{content}\n\n{instructions}",
                    }
                    break
            else:
                self.messages.insert(
                    0,
                    {
                        OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                        OpenAIMessageKeys.MESSAGE_CONTENT_KEY: instructions,
                    },
                )
        if self.mcp_toolkit.connected:
            names = ", ".join(mcpclient.name for mcpclient in self.mcp_toolkit.connected)
            self.append_message(
                role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY,
                content=f"Smarter added the tools of these MCP servers: {names}",
            )
        for name, error in self.mcp_toolkit.errors.items():
            self.append_message(
                role=OpenAIMessageKeys.SMARTER_ERROR_KEY,
                content=f"Smarter could not use the {name} MCP server: {error}",
            )

    def handle_function_provided(self, function: str) -> None:
        """
        Handle a function being provided.

        :param function: The name of the function that was provided.
        :type function: str

        :returns: None
        :rtype: None
        """
        logger.debug("%s.handle_function_provided() called with function: %s.", self.formatted_class_name, function)
        if self.tools is None:
            self.tools = []
        if self.available_functions is None:
            self.available_functions = {}

        if function == get_current_weather.__name__:
            weather_tool = weather_tool_factory()  # FIX NOTE: seems like this should be weather_tool_factory
            self.tools.append(weather_tool)
            self.available_functions[get_current_weather.__name__] = get_current_weather
            llm_tool_presented.send(sender=self.handle_function_provided, tool=weather_tool, plugin=None)
        elif function == date_calculator.__name__:
            date_calculator_tool = date_calculator_tool_factory()
            self.tools.append(date_calculator_tool)
            self.available_functions[date_calculator.__name__] = date_calculator
            llm_tool_presented.send(sender=self.handle_function_provided, tool=date_calculator_tool, plugin=None)
        elif function == calculator.__name__:
            calculator_tool = calculator_tool_factory()
            self.tools.append(calculator_tool)
            self.available_functions[calculator.__name__] = calculator
            llm_tool_presented.send(sender=self.handle_function_provided, tool=calculator_tool, plugin=None)

    def handle_completion(self) -> dict:
        """
        Handle prompt completion response.

        This method
        formats the final response to be returned to the client.

        :returns: A dictionary representing the final prompt completion response.
        :rtype: dict
        """
        logger.debug("%s.handle_completion() called", self.formatted_class_name)
        if not isinstance(self.second_iteration, dict):
            raise SmarterValueError(
                f"{self.formatted_class_name}: second_iteration must be a dictionary, got {type(self.second_iteration)}"
            )
        response = self.second_iteration.get(_InternalKeys.RESPONSE_KEY) or self.first_iteration.get(
            _InternalKeys.RESPONSE_KEY
        )
        if not isinstance(response, dict):
            raise SmarterValueError(f"{self.formatted_class_name}: response must be a dictionary, got {type(response)}")
        response["metadata"] = {"tool_calls": self.serialized_tool_calls, **self.request_meta_data}

        response[OpenAIMessageKeys.SMARTER_MESSAGE_KEY] = {
            "first_iteration": json.loads(json.dumps(self.first_iteration)),
            "second_iteration": json.loads(json.dumps(self.second_iteration)),
            _InternalKeys.PLUGINS_KEY: [plugin.plugin_meta.name for plugin in self.plugins or []],  # type: ignore[call-arg]
            _InternalKeys.MESSAGES_KEY: self.new_messages,
        }
        if self.tools:
            response_extended = response.get(OpenAIMessageKeys.SMARTER_MESSAGE_KEY).copy() or {}  # type: ignore[call-arg]
            response_extended[_InternalKeys.TOOLS_KEY] = [tool["function"]["name"] for tool in self.tools]
            response[OpenAIMessageKeys.SMARTER_MESSAGE_KEY] = response_extended
        return response

    def request_meta_data_factory(self):
        """
        Return a dictionary of request meta data.

        This includes
        the model, temperature, max_completion_tokens, and input_text.

        :returns: A dictionary of request meta data.
        :rtype: dict
        """
        logger.debug("%s.request_meta_data_factory() called.", self.formatted_class_name)
        return {
            _InternalKeys.MODEL_KEY: self.model,
            _InternalKeys.TEMPERATURE_KEY: self.temperature,
            _InternalKeys.MAX_COMPLETION_TOKENS_KEY: self.max_completion_tokens,
            "input_text": self.input_text,
        }

    def create_first_completion(self, completions_kwargs: dict[str, Any]) -> ChatCompletion:
        """
        Send the first request, which is the only one that offers the LLM tools.

        Some reasoning models reject function tools on v1/chat/completions unless reasoning_effort
        is 'none'. Requests with tools set reasoning_effort to 'none' for the models in
        :data:`TOOLS_REQUIRE_NO_REASONING_MODELS`. If another model rejects the request for that
        reason, it is retried once with reasoning_effort set to 'none' and the model is added to the set.
        """
        has_tools = bool(completions_kwargs.get(_InternalKeys.TOOLS_KEY))
        if has_tools and self.model in TOOLS_REQUIRE_NO_REASONING_MODELS:
            completions_kwargs[_InternalKeys.REASONING_EFFORT_KEY] = REASONING_EFFORT_NONE
        try:
            return openai.chat.completions.create(**completions_kwargs)  # type: ignore[call-arg]
        except openai.BadRequestError as e:
            if (
                not has_tools
                or _InternalKeys.REASONING_EFFORT_KEY in completions_kwargs
                or e.param != _InternalKeys.REASONING_EFFORT_KEY
            ):
                raise
            base_logger.warning(
                "%s %s - model %s rejected function tools at its default reasoning_effort. Retrying with reasoning_effort='%s'.",
                self.formatted_class_name,
                formatted_text("create_first_completion()"),
                self.model,
                REASONING_EFFORT_NONE,
            )
            TOOLS_REQUIRE_NO_REASONING_MODELS.add(str(self.model))
            completions_kwargs[_InternalKeys.REASONING_EFFORT_KEY] = REASONING_EFFORT_NONE
            return openai.chat.completions.create(**completions_kwargs)  # type: ignore[call-arg]

    def handler(
        self,
        user_profile: UserProfile,
        prompt: Prompt,
        data: Union[dict[str, Any], list],
        plugins: Optional[list[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> SmarterChatCompletionResponseType:
        """
        Process a prompt prompt request and invoke the appropriate OpenAI-compatible API endpoint.

        This method orchestrates the entire prompt completion workflow, including:

        - Validating input and internal state.
        - Initializing or updating the message thread.
        - Selecting and configuring plugins and/or functions (collectively, tool calls) for the LLM.
        - Preparing and sending requests to the OpenAI API (or compatible provider).
        - Handling tool calls and plugin responses.
        - Managing billing, logging, and signal dispatch.
        - Returning a formatted HTTP response with the LLM's output and relevant metadata.

        :param user_profile: The user_profile instance making the request.
        :type user_profile: UserProfile
        :param prompt: The prompt session instance associated with this request.
        :type prompt: Prompt
        :param data: The request payload, typically containing a session key and a list of message dictionaries.
        :type data: Union[dict[str, Any], list]

            Example::

                {
                    'session_key': '6f3bdd1981e0cac2de5fdc7afc2fb4e565826473a124153220e9f6bf49bca67b',
                    'messages': [
                        {'role': 'system', 'content': "You are a helpful assistant."},
                        {'role': 'assistant', 'content': "Welcome to Smarter! ..."},
                        {'role': 'smarter', 'content': "Tool call: smarter_plugin_0002({\"inquiry_type\":\"about\"})"},
                        {'role': 'user_profile', 'content': 'Hello, World!'}
                    ]
                }

        :param plugins: A list of plugin instances to be considered for selection and presentation to the LLM.
        :type plugins: Optional[list[PluginBase]]
        :param functions: A list of predefined function definitions for tool calls.
        :type functions: Optional[list[str]]

        :returns: An HTTP response dictionary (or list) containing the LLM's output, tool call results, and metadata.
        :rtype: SmarterChatCompletionResponseType

        :raises SmarterValueError: If required parameters are missing or invalid.
        :raises SmarterConfigurationError: If there are configuration issues with the provider or plugins.
        :raises SmarterIlligalInvocationError: If the method is invoked in an invalid state.

        .. note::

            This method manages both the initial and any required follow-up LLM requests (e.g., for tool calls).
            It also handles plugin selection logic and ensures that all required signals and billing events are triggered.

        .. seealso::

            :class:`_InternalKeys`
            :class:`OpenAIMessageKeys`
            :class:`PluginBase`
            :class:`ChatCompletion`
            :class:`ChatCompletionMessageToolCall`

        Example usage::

            response = provider.handler(
                prompt=chat_instance,
                data=request_data,
                plugins=[plugin1, plugin2],
                functions=[function_definition_1, function_definition_2],
                user_profile=current_user
            )
        """
        plugins_list = [plugin.name for plugin in plugins] if plugins else []
        logger.debug(
            "%s.handler() called with user_profile=%s, prompt=%s, plugins=%s, functions=%s",
            self.formatted_class_name,
            user_profile,
            prompt,
            plugins_list,
            functions,
        )
        self._chat = prompt
        self.user_profile = user_profile
        if prompt and prompt.user_profile:
            self._user_profile = prompt.user_profile
            self._account = prompt.user_profile.account
            self._user = prompt.user_profile.user
            logger.debug(
                "%s.handler() - reinitialized user_profile from prompt: %s, user_profile: %s",
                self.formatted_class_name,
                prompt,
                self._user_profile,
            )
        self.data = data  # type: ignore[assignment]
        self.plugins = plugins
        self.functions = functions

        prompt_started.send(sender=self.handler, prompt=self.prompt, data=self.data)
        # the status and the message of an error, e.g. a 400 from the LLM provider, if any.
        error_status: Optional[int] = None
        error_message: Optional[str] = None
        self.iteration = 1
        openai.api_key = self.api_key
        openai.base_url = self.base_url

        if not isinstance(self.prompt, Prompt):
            raise SmarterValueError(
                f"{self.formatted_class_name}: prompt must be an instance of Prompt, got {type(self.prompt)}"
            )

        try:
            self.validate()
            self.authorize_budgets()
            self.model = self.prompt.llmclient.default_model or self.default_model
            self.temperature = self.prompt.llmclient.default_temperature or self.default_temperature
            self.max_completion_tokens = self.prompt.llmclient.default_max_tokens or self.default_max_tokens
            if not self.data:
                raise SmarterValueError(f"{self.formatted_class_name}: data is required")
            self.input_text = self.get_input_text_prompt(data=self.data)
            self.request_meta_data = self.request_meta_data_factory()

            # initialize the message history from the persisted
            # message history in the database, if it exists,
            # and append the user_profile's message.
            #
            # using the persisted message history ensures that the prompt
            # provider has a consistent view of the conversation history
            # and that system and meta messages are preserved in their
            # original form and order.
            self.messages = self.db_message_history  # type: ignore[assignment]
            if self.messages:
                self.append_message(role=OpenAIMessageKeys.USER_MESSAGE_KEY, content=self.input_text)
            else:
                # new thread with no history, so we initialize with everything
                # that was passed in by the React front-end. There customarily
                # is 1 or more system messages, 1 or more assistant messages,
                # and a user_profile message.
                self.messages = self.get_message_thread(data=self.data)

            # run the llmclient's input guardrails on the user's message. A block raises
            # GuardrailBlockedError, which is answered with the guardrail's message below.
            self.handle_input_guardrails()

            # add plugins to the prompt if any are selected
            if self.plugins:
                for plugin in self.plugins:
                    if plugin.selected(user=self.user_profile.user, input_text=self.input_text, messages=self.messages):
                        self.handle_plugin_selected(plugin=plugin)

            # add the tools and instructions of the llmclient's MCP servers
            self.handle_mcp_clients()

            # add all functions that are included in the llmclient definition
            if self.functions:
                for function in self.functions:
                    self.handle_function_provided(function)

            self.prep_first_request()
            completions_kwargs = {
                _InternalKeys.MODEL_KEY: self.model,
                _InternalKeys.MESSAGES_KEY: self.openai_messages,
                _InternalKeys.TEMPERATURE_KEY: self.temperature,
                _InternalKeys.MAX_COMPLETION_TOKENS_KEY: self.max_completion_tokens,
            }
            if self.tools:
                # new rule: tool_choice should only be provided if there are
                # actual tools included in the request, otherwise OpenAI's
                # API returns a 400 error: 'Invalid value 'tool_choice'
                # is only allowed when 'tools' are specified.'
                completions_kwargs[_InternalKeys.TOOLS_KEY] = self.tools
                completions_kwargs[_InternalKeys.TOOL_CHOICE] = OPENAI_TOOL_CHOICE
            completions_kwargs = self.prune_empty_values(completions_kwargs)

            logger.debug(
                "%s %s - openai.chat.completions.create() completions_kwargs: %s",
                self.formatted_class_name,
                formatted_text("handler()"),
                completions_kwargs,
            )

            self.first_response = self.create_first_completion(completions_kwargs)
            if not isinstance(self.first_response, ChatCompletion):
                raise SmarterValueError(
                    f"{self.formatted_class_name}: first_response must be a ChatCompletion, got {type(self.first_response)}"
                )
            if self.first_response.choices and self.first_response.choices[0].message.tool_calls is None:
                # this is the final response, so the output guardrails run on it
                self.first_response = self.handle_output_guardrails(self.first_response)
            self.handle_response()
            self.append_openai_response(self.first_response)
            response_message = self.first_response.choices[0].message
            if not isinstance(response_message, ChatCompletionMessage):
                raise SmarterValueError(
                    f"{self.formatted_class_name}: response_message must be a ChatCompletionMessage, got {type(response_message)}"
                )

            if response_message.tool_calls is not None:
                tool_calls: Optional[list[ChatCompletionMessageToolCallUnion]] = response_message.tool_calls
                logger.debug(
                    "%s %s - %s tool calls detected, preparing second request",
                    self.formatted_class_name,
                    formatted_text("handler()"),
                    len(tool_calls),
                )
                self.iteration = 2
                self.serialized_tool_calls = []

                for tool_call in tool_calls:
                    self.process_tool_call(tool_call)

                self.prep_second_request()

                if not isinstance(self.model, str):
                    raise SmarterConfigurationError(
                        f"{self.formatted_class_name}: model must be a string, got {type(self.model)}"
                    )
                if not isinstance(self.openai_messages, list):
                    raise SmarterConfigurationError(
                        f"{self.formatted_class_name}: openai_messages must be a list, got {type(self.openai_messages)}"
                    )
                if not isinstance(self.temperature, (float, int)):
                    raise SmarterConfigurationError(
                        f"{self.formatted_class_name}: temperature must be a float or int, got {type(self.temperature)}"
                    )
                if not isinstance(self.max_completion_tokens, int):
                    raise SmarterConfigurationError(
                        f"{self.formatted_class_name}: max_completion_tokens must be an int, got {type(self.max_completion_tokens)}"
                    )
                self.second_response = openai.chat.completions.create(
                    model=self.model,
                    messages=self.openai_messages,  # type: ignore[call-arg]
                    temperature=self.temperature,
                    max_completion_tokens=self.max_completion_tokens,
                )
                self.second_response = self.handle_output_guardrails(self.second_response)
                self.append_openai_response(self.second_response)
                self.handle_response()

        # an input guardrail blocked the user's message, so the LLM is not called
        except GuardrailBlockedError as blocked:
            created_time = int(time.time())
            self.iteration = 1
            self.first_response = ChatCompletion(
                id="guardrail_blocked",
                model=self.model or "unknown",
                choices=[
                    Choice(
                        message=ChatCompletionMessage(
                            role=OpenAIMessageKeys.ASSISTANT_MESSAGE_KEY, content=blocked.message
                        ),
                        finish_reason="content_filter",
                        index=0,
                    )
                ],
                usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                system_fingerprint="guardrail_blocked_" + str(created_time),
                created=created_time,
                object="chat.completion",
            )
            self.handle_response()
            self.append_openai_response(self.first_response)

        # a budget forbids more charges, so the LLM is not called, and the person is told why.
        except SmarterBudgetExceeded as exceeded:
            created_time = int(time.time())
            self.iteration = 1
            self.first_response = ChatCompletion(
                id="budget_exceeded",
                model=self.model or "unknown",
                choices=[
                    Choice(
                        message=ChatCompletionMessage(
                            role=OpenAIMessageKeys.ASSISTANT_MESSAGE_KEY, content=exceeded.message
                        ),
                        finish_reason="stop",
                        index=0,
                    )
                ],
                usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                system_fingerprint="budget_exceeded_" + str(created_time),
                created=created_time,
                object="chat.completion",
            )
            self.handle_response()
            self.append_openai_response(self.first_response)

        # handle anything that went wrong
        # pylint: disable=broad-exception-caught
        except Exception as e:
            stack_trace = traceback.format_exc()
            chat_response_failure.send(
                sender=self.handler,
                iteration=self.iteration,
                prompt=self.prompt,
                request_meta_data=self.request_meta_data,
                exception=e,
                first_iteration=self.first_iteration,
                second_iteration=self.second_iteration,
                messages=self.messages,
                stack_trace=stack_trace,
            )
            error_status, error_message = exception_status_and_message(e)
            created_time = int(time.time())
            self.first_response = ChatCompletion(
                id="error_response",
                model=self.model or "unknown",
                choices=[
                    Choice(
                        message=ChatCompletionMessage(
                            role=OpenAIMessageKeys.ASSISTANT_MESSAGE_KEY, content=error_message
                        ),
                        finish_reason="stop",
                        index=0,
                    )
                ],
                usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                system_fingerprint="error_response_" + str(created_time),
                created=created_time,
                object="chat.completion",
            )
            self.handle_response()
            self.append_openai_error_response(self.first_response, e)

        # done! for better or worse. An error is kept in the message history, so that the
        # prompt engineers workbench can display it, and is returned with its own status,
        # e.g. the status of the LLM provider's error response, and its message.
        response = self.handle_completion()

        prompt_finished.send(
            sender=self.handler,
            prompt=self.prompt,
            request=self.first_iteration.get(_InternalKeys.REQUEST_KEY),
            response=response,
            messages=self.messages,
        )
        if error_status is not None and error_status != HTTPStatus.OK.value:
            retval = http_response_factory(
                status=error_status,
                body={"error": {"status": error_status, "message": error_message}, "response": response},
            )
        else:
            retval = http_response_factory(status=HTTPStatus.OK, body=response)
        if not isinstance(retval, dict):
            raise SmarterValueError(
                f"{self.formatted_class_name}: http_response_factory() should have returned a dictionary, but instead returned {type(retval)}"
            )
        return retval
