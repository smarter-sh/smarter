"""
Base class for chat providers.
"""

import json
import logging
from http import HTTPStatus
from typing import Dict, List, Optional

# 3rd party stuff
import openai
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)

from smarter.apps.account.models import (
    CHARGE_TYPE_PLUGIN,
    CHARGE_TYPE_PROMPT_COMPLETION,
    CHARGE_TYPE_TOOL,
)
from smarter.apps.chat.functions.function_weather import (
    get_current_weather,
    weather_tool_factory,
)
from smarter.apps.chat.models import Chat

# smarter chat provider stuff
from smarter.apps.chat.providers.utils import (
    ensure_system_role_present,
    exception_response_factory,
    get_request_body,
    http_response_factory,
    parse_request,
)
from smarter.apps.chat.signals import (
    chat_completion_plugin_called,
    chat_completion_request,
    chat_completion_response,
    chat_completion_tool_called,
    chat_finished,
    chat_provider_initialized,
    chat_response_failure,
    chat_started,
)
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.common.exceptions import (
    SmarterConfigurationError,
    SmarterIlligalInvocationError,
    SmarterValueError,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.helpers.llm import get_date_time_string
from smarter.lib.django.user import UserType

from .const import OpenAIMessageKeys
from .mixins import ProviderDbMixin


logger = logging.getLogger(__name__)

# 1.) EXCEPTION_MAP: A dictionary that maps exceptions to HTTP status codes and error types.
# Base exception map for chat providers. This maps internally raised exceptions to HTTP status codes.
BASE_EXCEPTION_MAP = {
    SmarterValueError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    SmarterConfigurationError: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
    SmarterIlligalInvocationError: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
    ValueError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    TypeError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    NotImplementedError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    Exception: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
}

EXCEPTION_MAP = BASE_EXCEPTION_MAP.copy()
EXCEPTION_MAP[openai.APIError] = (HTTPStatus.BAD_REQUEST, "BadRequestError")
EXCEPTION_MAP[openai.OpenAIError] = (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError")
EXCEPTION_MAP[openai.ConflictError] = (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError")
EXCEPTION_MAP[openai.NotFoundError] = (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError")
EXCEPTION_MAP[openai.APIStatusError] = (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError")
EXCEPTION_MAP[openai.RateLimitError] = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "InternalServerError")
EXCEPTION_MAP[openai.APITimeoutError] = (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError")
EXCEPTION_MAP[openai.BadRequestError] = (HTTPStatus.BAD_REQUEST, "BadRequestError")
EXCEPTION_MAP[openai.APIConnectionError] = (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError")
EXCEPTION_MAP[openai.AuthenticationError] = (HTTPStatus.UNAUTHORIZED, "UnauthorizedError")
EXCEPTION_MAP[openai.InternalServerError] = (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError")
EXCEPTION_MAP[openai.PermissionDeniedError] = (HTTPStatus.UNAUTHORIZED, "UnauthorizedError")
EXCEPTION_MAP[openai.LengthFinishReasonError] = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "RequestEntityTooLargeError")
EXCEPTION_MAP[openai.UnprocessableEntityError] = (HTTPStatus.BAD_REQUEST, "BadRequestError")
EXCEPTION_MAP[openai.APIResponseValidationError] = (HTTPStatus.BAD_REQUEST, "BadRequestError")
EXCEPTION_MAP[openai.ContentFilterFinishReasonError] = (HTTPStatus.BAD_REQUEST, "BadRequestError")

OPENAI_TOOL_CHOICE = "auto"
SMARTER_SYSTEM_KEY_PREFIX = "smarter_"


class InternalKeys:
    """
    Internal dict keys used in the chat provider.
    """

    REQUEST_KEY = "request"
    RESPONSE_KEY = "response"
    TOOLS_KEY = "tools"
    MESSAGES_KEY = "messages"
    PLUGINS_KEY = "plugins"
    MODEL_KEY = "model"
    TEMPERATURE_KEY = "temperature"
    MAX_TOKENS_KEY = "max_tokens"

    SMARTER_PLUGIN_KEY = SMARTER_SYSTEM_KEY_PREFIX + "plugin"
    SMARTER_IS_NEW = SMARTER_SYSTEM_KEY_PREFIX + "is_new"


class ChatProviderBase(ProviderDbMixin):
    """
    Base class for all chat providers.

    Attributes:
        chat: The chat instance.
        data: The request data.
        plugins: A list of plugins.
        model: The model to use for chat completions.
        temperature: The temperature to use for chat completions.
        max_tokens: The maximum tokens to use for chat completions.
        input_text: The input text for the chat completion.
        completion_tokens: The number of completion tokens used.
        prompt_tokens: The number of prompt tokens used.
        total_tokens: The total number of tokens used.
        reference: The reference for the chat completion.
        iteration: The iteration number.
        request_meta_data: The request meta data.
        first_iteration: The first iteration request and response.
        first_response: The first response.
        second_response: The second response.
        second_iteration: The second iteration request and response.
        serialized_tool_calls: A list of serialized tool calls.
        tools: A list of tools.
        available_functions: A dictionary of available functions.
    """

    __slots__ = (
        "_provider",
        "_default_model",
        "_default_system_role",
        "_default_temperature",
        "_default_max_tokens",
        "_valid_chat_completion_models",
        "_messages",
        "_base_url",
        "_api_key",
        "chat",
        "data",
        "plugins",
        "model",
        "temperature",
        "max_tokens",
        "input_text",
        "completion_tokens",
        "prompt_tokens",
        "total_tokens",
        "reference",
        "iteration",
        "request_meta_data",
        "first_iteration",
        "first_response",
        "second_iteration",
        "second_response",
        "serialized_tool_calls",
        "tools",
        "available_functions",
    )

    _provider: str
    _default_model: str
    _default_system_role: str
    _default_temperature: float
    _default_max_tokens: int

    _valid_chat_completion_models: list[str]
    _messages: List[Dict[str, str]]

    _base_url: str
    _api_key: str

    data: dict
    plugins: Optional[List[PluginStatic]]

    model: str
    temperature: float
    max_tokens: int
    input_text: str

    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    reference: str

    iteration: int
    request_meta_data: dict
    first_iteration: dict
    first_response: ChatCompletion
    second_response: ChatCompletion
    second_iteration: dict
    serialized_tool_calls: list[dict]

    # built-in tools that we make available to all providers
    tools: list[dict]
    available_functions: dict

    def __init__(
        self,
        provider: str,
        base_url: str,
        api_key: str,
        default_model: str,
        default_system_role: str,
        default_temperature: float,
        default_max_tokens: int,
        valid_chat_completion_models: list[str],
        add_built_in_tools: bool,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.init()
        self.chat = kwargs.get("chat")
        self._provider = provider
        self._base_url = base_url
        self._api_key = api_key

        self._default_model = default_model
        self._default_system_role = default_system_role
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens
        self._valid_chat_completion_models = valid_chat_completion_models

        weather_tool = weather_tool_factory()
        self.tools: list[dict] = [weather_tool] if add_built_in_tools else []
        self.available_functions = (
            {
                "get_current_weather": get_current_weather,
            }
            if add_built_in_tools
            else {}
        )

        chat_provider_initialized.send(sender=self)

    def init(self):
        super().init()
        self._default_model = None
        self._default_system_role = None
        self._default_temperature = None
        self._default_max_tokens = None

        self._valid_chat_completion_models = None
        self._messages = []

        self._base_url = None
        self._api_key = None

        self.chat = None
        self.data = None
        self.plugins = []

        self.model = None
        self.temperature = None
        self.max_tokens = None
        self.input_text = None

        self.completion_tokens = None
        self.prompt_tokens = None
        self.total_tokens = None
        self.reference = None

        self.iteration = 1
        self.request_meta_data = {}
        self.first_iteration = {
            InternalKeys.REQUEST_KEY: None,
            InternalKeys.RESPONSE_KEY: None,
        }
        self.first_response = None
        self.second_response = None
        self.second_iteration = {
            InternalKeys.REQUEST_KEY: {InternalKeys.MESSAGES_KEY: []},
            InternalKeys.RESPONSE_KEY: {},
            InternalKeys.MESSAGES_KEY: [],
        }

        self.serialized_tool_calls = None

    def validate(self):

        if not self.chat:
            raise SmarterValueError(f"{self.formatted_class_name}: chat object is required")
        if not self.data:
            raise SmarterValueError(f"{self.formatted_class_name}: data object is required")
        if not self.user:
            raise SmarterValueError(f"{self.formatted_class_name}: user object is required")
        if not self.default_model:
            raise SmarterValueError(f"{self.formatted_class_name}: default_model is required")
        if not self.default_system_role:
            raise SmarterValueError(f"{self.formatted_class_name}: default_system_role is required")
        if not self.default_temperature:
            raise SmarterValueError(f"{self.formatted_class_name}: default_temperature is required")
        if not self.default_max_tokens:
            raise SmarterValueError(f"{self.formatted_class_name}: default_max_tokens is required")

        if self.default_model not in self.valid_chat_completion_models:
            raise SmarterValueError(
                f"Internal error. Invalid default model: {self.default_model} not found in list of valid {self.provider} models {self.valid_chat_completion_models}."
            )

        if not self.account:
            self.account = self.chat.account

    @property
    def ready(self) -> bool:
        return self.chat and self.data and self.account

    @property
    def messages(self) -> List[Dict[str, str]]:
        return self._messages

    @messages.setter
    def messages(self, value: List[Dict[str, str]]) -> None:
        self._messages = value

    @property
    def formatted_class_name(self):
        identifier = self.__class__.__name__ + f"({id(self)})"
        return formatted_text(identifier)

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def default_system_role(self) -> str:
        return self._default_system_role

    @property
    def default_temperature(self) -> float:
        return self._default_temperature

    @property
    def default_max_tokens(self) -> int:
        return self._default_max_tokens

    @property
    def valid_chat_completion_models(self) -> list[str]:
        return self._valid_chat_completion_models

    def messages_set_is_new(self, messages: list[dict], is_new: bool = False) -> list[dict]:
        """
        Set the is_new flag for all messages in the message thread.
        """
        retval = []
        for message in messages:
            new_message = message.copy()
            new_message[InternalKeys.SMARTER_IS_NEW] = is_new
            retval.append(new_message)
        return retval

    def get_message_thread(self, data: dict) -> List[Dict[str, str]]:
        """
        Initialize a new message thread with a system prompt
        and the incoming data.
        """
        default_system_role = get_date_time_string()
        default_system_role += self.chat.chatbot.default_system_role_enhanced or self.default_system_role
        request_body = get_request_body(data=data)
        client_message_thread, _ = parse_request(request_body)
        client_message_thread = ensure_system_role_present(
            messages=client_message_thread, default_system_role=default_system_role
        )
        retval = self.messages_set_is_new(client_message_thread, is_new=False)
        logger.info("get_message_thread() - client_message_thread: %s", retval)
        return retval

    def get_input_text_prompt(self, data: dict) -> str:
        request_body = get_request_body(data=data)
        _, input_text = parse_request(request_body)
        return input_text

    def append_message(self, role: str, content: str, message: dict = None) -> None:
        if role not in OpenAIMessageKeys.all_roles:
            raise SmarterValueError(
                f"Internal error. Invalid message role: {role} not found in list of valid {self.provider} message roles {OpenAIMessageKeys.all_roles}."
            )
        if not content and not message:
            logger.warning("append_message() - content and message are both empty. Skipping.")
            return
        message = message or {}
        new_message = message.copy()
        new_message[OpenAIMessageKeys.MESSAGE_ROLE_KEY] = role
        new_message[OpenAIMessageKeys.MESSAGE_CONTENT_KEY] = content
        new_message[InternalKeys.SMARTER_IS_NEW] = True
        self.messages.append(new_message)

    def append_message_plugin_selected(self, plugin: str) -> None:
        content = f"Smarter selected this plugin: {plugin}"
        self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

    def append_message_tool_called(self, function_name: str, function_args: str) -> None:
        content = f"{self.provider} called this tool: {function_name}({function_args})"
        self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

    def _insert_charge_by_type(self, charge_type: str) -> None:
        self.db_insert_charge(
            provider=self.provider,
            charge_type=charge_type,
            completion_tokens=self.completion_tokens,
            prompt_tokens=self.prompt_tokens,
            total_tokens=self.total_tokens,
            model=self.model,
            reference=self.reference,
        )


class OpenAICompatibleChatProvider(ChatProviderBase):
    """
    A chat provider that works with any vendor provider that is
    fully compatible with OpenAI's text completion API.
    """

    @property
    def openai_messages(self) -> list:
        filtered = [
            message for message in self.messages if message[OpenAIMessageKeys.MESSAGE_ROLE_KEY] in OpenAIMessageKeys.all
        ]
        retval = []
        for message in filtered:
            message_copy = message.copy()
            if InternalKeys.SMARTER_IS_NEW in message_copy:
                del message_copy[InternalKeys.SMARTER_IS_NEW]
            retval.append(message_copy)
        return retval

    @property
    def new_messages(self) -> list:
        try:
            return [message for message in self.messages if message[InternalKeys.SMARTER_IS_NEW]]
        except KeyError:
            prefix = formatted_text(f"{self.formatted_class_name} new_messages()")
            logger.error(
                "%s - KeyError: '%s' key not found in message: %s", prefix, InternalKeys.SMARTER_IS_NEW, self.messages
            )
            return self.messages

    def prep_first_request(self):
        logger.info("%s %s", self.formatted_class_name, formatted_text("prep_first_request()"))
        # ensure that all message history is marked as not new
        self.messages = self.messages_set_is_new(self.messages, is_new=False)
        tool_choice = OPENAI_TOOL_CHOICE
        self.first_iteration[InternalKeys.REQUEST_KEY] = {
            InternalKeys.MODEL_KEY: self.model,
            InternalKeys.MESSAGES_KEY: self.openai_messages,
            InternalKeys.TOOLS_KEY: self.tools,
            InternalKeys.TEMPERATURE_KEY: self.temperature,
            InternalKeys.MAX_TOKENS_KEY: self.max_tokens,
            "tool_choice": tool_choice,
        }

        # create a Smarter UI message with the established configuration
        content = f"Prompt configuration: llm={self.provider}, model={self.model}, temperature={self.temperature}, max_tokens={self.max_tokens}, tool_choice={tool_choice}."
        self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

        # for any tools that are included in the request, add Smarter UI messages for each tool
        if self.tools:
            for tool in self.tools:
                tool_type = tool.get("type")
                this_tool = tool.get(tool_type) or {}
                tool_name = this_tool.get("name") or "error: missing name"
                tool_description = this_tool.get("description") or "error: missing description"
                tool_parameters = this_tool.get("parameters", {}).get("properties", {})
                inputs = []
                for parameter, details in tool_parameters.items():
                    if "description" in details:
                        inputs.append(f"{parameter}: {details['description']}")
                    elif "enum" in details:
                        inputs.append(f"{parameter}: {', '.join(details['enum'])}")

                inputs = ", ".join(inputs)
                content = f"Tool presented: {tool_name}({inputs}) - {tool_description} "
                self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

        # send a chat completion request signal. this triggers a variety of db records to be created
        # asynchronously in the background via Celery tasks.
        chat_completion_request.send(
            sender=self.handler,
            chat=self.chat,
            iteration=self.iteration,
            request=self.first_iteration[InternalKeys.REQUEST_KEY],
        )

    def prep_second_request(self):
        logger.info("%s %s", self.formatted_class_name, formatted_text("prep_second_request()"))
        self.second_iteration[InternalKeys.REQUEST_KEY] = {
            InternalKeys.MODEL_KEY: self.model,
            InternalKeys.MESSAGES_KEY: self.openai_messages,
        }
        chat_completion_request.send(
            sender=self.handler,
            chat=self.chat,
            iteration=self.iteration,
            request=self.second_iteration[InternalKeys.REQUEST_KEY],
        )

    def append_openai_response(self, response: ChatCompletion) -> None:
        response_message = response.choices[0].message
        message_json = json.loads(response_message.model_dump_json())
        self.append_message(role=response_message.role, content=response_message.content, message=message_json)

    def handle_response(self) -> None:
        """
        handle internal billing, and append messages to the response for prompt completion and the billing summary

        """
        logger.info(
            "%s %s", self.formatted_class_name, formatted_text(f"handle_response() iteration: {self.iteration}")
        )

        response = self.second_response if self.iteration == 2 else self.first_response

        self.prompt_tokens = response.usage.prompt_tokens
        self.completion_tokens = response.usage.completion_tokens
        self.total_tokens = response.usage.total_tokens
        self.reference = response.system_fingerprint

        self._insert_charge_by_type(CHARGE_TYPE_PROMPT_COMPLETION)
        self.append_message(
            role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY,
            content=f"{self.provider} prompt charges: {self.prompt_tokens} prompt tokens, {self.completion_tokens} completion tokens = {self.total_tokens} total tokens charged.",
        )

        if self.iteration == 1:
            self.first_iteration[InternalKeys.RESPONSE_KEY] = json.loads(self.first_response.model_dump_json())
        if self.iteration == 2:
            self.second_iteration[InternalKeys.RESPONSE_KEY] = json.loads(self.second_response.model_dump_json())

        serialized_request = (
            self.first_iteration[InternalKeys.REQUEST_KEY]
            if self.iteration == 1
            else self.second_iteration[InternalKeys.REQUEST_KEY]
        )
        serialized_response = (
            self.first_iteration[InternalKeys.RESPONSE_KEY]
            if self.iteration == 1
            else self.second_iteration[InternalKeys.RESPONSE_KEY]
        )

        chat_completion_response.send(
            sender=self.handler,
            chat=self.chat,
            iteration=self.iteration,
            request=serialized_request,
            response=serialized_response,
            messages=self.messages,
        )

    def handle_tool_called(self, function_name: str, function_args: str) -> None:
        """
        handle a built-in tool call. example: get_current_weather()
        """
        logger.info("%s %s - %s", self.formatted_class_name, formatted_text("handle_tool_called()"), function_name)
        request = (self.first_iteration[InternalKeys.REQUEST_KEY],)
        response = (self.first_iteration[InternalKeys.RESPONSE_KEY],)
        chat_completion_tool_called.send(
            sender=self.handler,
            chat=self.chat,
            plugin=None,
            function_name=function_name,
            function_args=function_args,
            request=request,
            response=response,
        )
        self._insert_charge_by_type(CHARGE_TYPE_TOOL)
        self.db_insert_chat_tool_call(
            function_name=function_name, function_args=function_args, request=request, response=response
        )

    def handle_plugin_called(self, plugin: PluginStatic) -> None:
        logger.info("%s %s - %s", self.formatted_class_name, formatted_text("handle_plugin_called()"), plugin.name)
        chat_completion_plugin_called.send(
            sender=self.handler,
            chat=self.chat,
            plugin=plugin,
            input_text=self.input_text,
        )
        self._insert_charge_by_type(CHARGE_TYPE_PLUGIN)
        self.db_insert_chat_plugin_usage(chat=self.chat, plugin=plugin, input_text=self.input_text)

    def process_tool_call(self, tool_call: ChatCompletionMessageToolCall):
        """
        tool_call: List[ChatCompletionMessageToolCall]
        """
        logger.info("%s %s", self.formatted_class_name, formatted_text("process_tool_call()"))
        if not tool_call:
            logger.warning("process_tool_call() - tool_call is empty. Skipping.")
            return
        serialized_tool_call = {}
        plugin: PluginStatic = None
        function_name = tool_call.function.name
        function_to_call = self.available_functions[function_name]
        function_args = json.loads(tool_call.function.arguments)
        serialized_tool_call["function_name"] = function_name
        serialized_tool_call["function_args"] = function_args
        self.append_message_tool_called(function_name=function_name, function_args=function_args)

        function_response = None
        if function_name == "get_current_weather":
            function_response = function_to_call(
                location=function_args.get("location"),
                unit=function_args.get("unit"),
            )
            self.handle_tool_called(function_name=function_name, function_args=function_args)
        elif function_name.startswith("function_calling_plugin"):
            # FIX NOTE: we should revisit this. technically, we're supposed to be calling
            # function_to_call, assigned above. but just to play it safe,
            # we're directly invoking the plugin's function_calling_plugin() method.
            plugin_id = int(function_name[-4:])
            plugin = PluginStatic(plugin_id=plugin_id, user_profile=self.user_profile)
            plugin.params = function_args
            function_response = plugin.function_calling_plugin(inquiry_type=function_args.get("inquiry_type"))
            serialized_tool_call[InternalKeys.SMARTER_PLUGIN_KEY] = PluginMetaSerializer(plugin.plugin_meta).data
            self.handle_plugin_called(plugin=plugin)
        tool_call_message = {
            "tool_call_id": tool_call.id,
            OpenAIMessageKeys.MESSAGE_NAME_KEY: function_name,
        }
        self.append_message(
            role=OpenAIMessageKeys.TOOL_MESSAGE_KEY, content=function_response, message=tool_call_message
        )
        self.serialized_tool_calls.append(serialized_tool_call)

    def handle_plugin_selected(self, plugin: PluginStatic) -> None:
        # does the prompt have anything to do with any of the search terms defined in a plugin?
        # FIX NOTE: need to decide on how to resolve which of many plugin values sets to use for model, temperature, max_tokens
        logger.info("%s %s", self.formatted_class_name, formatted_text("handle_plugin_selected()"))
        logger.warning(
            "smarter.apps.chat.providers.base_classes.OpenAICompatibleChatProvider.handler(): plugins selector needs to be refactored to use Django model."
        )
        self.model = plugin.plugin_prompt.model
        self.temperature = plugin.plugin_prompt.temperature
        self.max_tokens = plugin.plugin_prompt.max_tokens
        self.messages = plugin.customize_prompt(self.messages)
        self.tools.append(plugin.custom_tool)
        self.available_functions[plugin.function_calling_identifier] = plugin.function_calling_plugin
        self.append_message_plugin_selected(plugin=plugin.plugin_meta.name)
        # note to self: Plugin sends a plugin_selected signal, so no need to send it here.

    def handle_success(self) -> dict:
        logger.info("%s %s", self.formatted_class_name, formatted_text("handle_success()"))
        response = self.second_iteration.get(InternalKeys.RESPONSE_KEY) or self.first_iteration.get(
            InternalKeys.RESPONSE_KEY
        )
        response["metadata"] = {"tool_calls": self.serialized_tool_calls, **self.request_meta_data}

        response[OpenAIMessageKeys.SMARTER_MESSAGE_KEY] = {
            "first_iteration": json.loads(json.dumps(self.first_iteration)),
            "second_iteration": json.loads(json.dumps(self.second_iteration)),
            InternalKeys.TOOLS_KEY: [tool["function"]["name"] for tool in self.tools],
            InternalKeys.PLUGINS_KEY: [plugin.plugin_meta.name for plugin in self.plugins],
            InternalKeys.MESSAGES_KEY: self.new_messages,
        }
        return response

    def request_meta_data_factory(self):
        """
        Return a dictionary of request meta data.
        """
        logger.info("%s %s", self.formatted_class_name, formatted_text("request_meta_data_factory()"))
        return {
            InternalKeys.MODEL_KEY: self.model,
            InternalKeys.TEMPERATURE_KEY: self.temperature,
            InternalKeys.MAX_TOKENS_KEY: self.max_tokens,
            "input_text": self.input_text,
        }

    def handler(self, chat: Chat, data: dict, plugins: list[PluginStatic], user: UserType) -> dict:
        """
        Chat prompt handler. Responsible for processing incoming requests and
        invoking the appropriate OpenAI API endpoint based on the contents of
        the request.

        Args:
            chat: Chat instance
            data: Request data (see below)
            plugins: a List of plugins to potentially show to the LLM
            user: User instance

        data: {
            'session_key': '6f3bdd1981e0cac2de5fdc7afc2fb4e565826473a124153220e9f6bf49bca67b',
            'messages': [
                    {
                        'role': 'system',
                        'content': "You are a helpful assistant."
                    },
                    {
                        'role': 'assistant',
                        'content': "Welcome to Smarter!. Following are some example prompts: blah blah blah"
                    },
                    {   "role": "smarter",
                        "content": "Tool call: function_calling_plugin_0002({\"inquiry_type\":\"about\"})"}
                    {
                        'role': 'user',
                        'content': 'Hello, World!'
                    }
                ]
            }
        """
        logger.info("%s %s", self.formatted_class_name, formatted_text("handler()"))
        self.chat = chat
        if chat:
            self.account = chat.account
        self.data = data
        self.plugins = plugins
        self.user = user

        chat_started.send(sender=self.handler, chat=self.chat, data=self.data)
        self.iteration = 1
        openai.api_key = self.api_key
        openai.base_url = self.base_url

        try:
            self.validate()
            self.model = self.chat.chatbot.default_model or self.default_model
            self.temperature = self.chat.chatbot.default_temperature or self.default_temperature
            self.max_tokens = self.chat.chatbot.default_max_tokens or self.default_max_tokens
            self.input_text = self.get_input_text_prompt(data=self.data)
            self.request_meta_data = self.request_meta_data_factory()

            # initialize the message history from the persisted
            # message history in the database, if it exists,
            # and append the user's message.
            #
            # using the persisted message history ensures that the chat
            # provider has a consistent view of the conversation history
            # and that system and meta messages are preserved in their
            # original form and order.
            self.messages = self.db_message_history
            if self.messages:
                self.append_message(role=OpenAIMessageKeys.USER_MESSAGE_KEY, content=self.input_text)
            else:
                # new thread with no history, so we initialize with everything
                # that was passed in by the React front-end. There customarily
                # is 1 or more system messages, 1 or more assistant messages,
                # and a user message.
                logger.info("hi fuckhead.")
                self.messages = self.get_message_thread(data=self.data)

            for plugin in self.plugins:
                if plugin.selected(user=self.user, input_text=self.input_text):
                    self.handle_plugin_selected(plugin=plugin)

            self.prep_first_request()

            self.first_response = openai.chat.completions.create(
                model=self.model,
                messages=self.openai_messages,
                tools=self.tools,
                tool_choice=OPENAI_TOOL_CHOICE,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            self.handle_response()
            self.append_openai_response(self.first_response)
            response_message = self.first_response.choices[0].message
            tool_calls: list[ChatCompletionMessageToolCall] = response_message.tool_calls
            if tool_calls:
                # extend conversation with assistant's reply
                response = json.loads(response_message.model_dump_json())
                response[InternalKeys.SMARTER_IS_NEW] = True
                self.iteration = 2
                self.serialized_tool_calls = []

                for tool_call in tool_calls:
                    self.process_tool_call(tool_call)

                self.prep_second_request()

                self.second_response = openai.chat.completions.create(
                    model=self.model,
                    messages=self.openai_messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                self.append_openai_response(self.second_response)
                self.handle_response()

        # handle anything that went wrong
        # pylint: disable=broad-exception-caught
        except Exception as e:
            chat_response_failure.send(
                sender=self.handler,
                iteration=self.iteration,
                chat=self.chat,
                request_meta_data=self.request_meta_data,
                exception=e,
                first_iteration=self.first_iteration,
                second_iteration=self.second_iteration,
                messages=self.messages,
            )
            status_code, _message = EXCEPTION_MAP.get(
                type(e), (HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
            )
            return http_response_factory(
                status_code=status_code,
                body=exception_response_factory(exception=e, request_meta_data=self.request_meta_data),
            )

        # success!! return the response
        response = self.handle_success()

        chat_finished.send(
            sender=self.handler,
            chat=self.chat,
            request=self.first_iteration.get(InternalKeys.REQUEST_KEY),
            response=response,
            messages=self.messages,
        )
        return http_response_factory(status_code=HTTPStatus.OK, body=response)
