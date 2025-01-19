"""
Base class for chat providers.
"""

import json
import logging
from http import HTTPStatus
from typing import Any, Dict, List, Optional

# 3rd party stuff
import openai
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)

from smarter.apps.account.tasks import (
    create_plugin_charge,
    create_prompt_completion_charge,
)
from smarter.apps.chat.functions.function_weather import (
    get_current_weather,
    weather_tool_factory,
)
from smarter.apps.chat.models import Chat

# smarter chat provider stuff
from smarter.apps.chat.providers.utils import (
    clean_messages,
    ensure_system_role_present,
    exception_response_factory,
    get_request_body,
    http_response_factory,
    parse_request,
    request_meta_data_factory,
)
from smarter.apps.chat.signals import (
    chat_completion_request,
    chat_completion_response,
    chat_completion_tool_called,
    chat_invocation_finished,
    chat_invocation_start,
    chat_provider_initialized,
    chat_response_failure,
)
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.common.exceptions import (
    SmarterConfigurationError,
    SmarterIlligalInvocationError,
    SmarterValueError,
)
from smarter.common.helpers.console_helpers import formatted_text
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


class InternalKeys:
    """
    Internal dict keys used in the chat provider.
    """

    REQUEST_KEY = "request"
    RESPONSE_KEY = "response"
    TOOLS_KEY = "tools"
    MESSAGES_KEY = "messages"
    PLUGINS_KEY = "plugins"


class OpenAICompatibleChatProvider(ProviderDbMixin):
    """
    Base class for chat providers.
    """

    __slots__ = (
        "_name",
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
        "user",
        "iteration",
        "request_meta_data",
        "first_iteration",
        "first_response",
        "second_response",
        "second_iteration",
        "first_response_dict",
        "second_response_dict",
        "serialized_tool_calls",
        "input_text",
        "weather_tool",
        "tools",
        "available_functions",
    )

    _name: str
    _default_model: str
    _default_system_role: str
    _default_temperature: float
    _default_max_tokens: int

    _valid_chat_completion_models: list[str]
    _messages: List[Dict[str, str]]

    _base_url: str
    _api_key: str

    chat: Chat
    data: dict
    plugins: Optional[List[PluginStatic]]
    user: Optional[Any]

    iteration: int
    request_meta_data: dict
    first_iteration: dict
    first_response: ChatCompletion
    second_response: ChatCompletion
    second_iteration: dict
    first_response_dict: dict
    second_response_dict: dict
    serialized_tool_calls: list[dict]
    input_text: str

    # built-in tools that we make available to all providers
    tools: list
    available_functions: dict

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        default_model: str,
        default_system_role: str,
        default_temperature: float,
        default_max_tokens: int,
        valid_chat_completion_models: list[str],
    ):
        self.init()
        self._name = name
        self._base_url = base_url
        self._api_key = api_key

        self._default_model = default_model
        self._default_system_role = default_system_role
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens
        self._valid_chat_completion_models = valid_chat_completion_models

        chat_provider_initialized.send(sender=self)

    def init(self):
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
        self.plugins = None
        self.user = None

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

        self.first_response_dict = None
        self.second_response_dict = None
        self.serialized_tool_calls = None
        self.input_text = None

        self.chat = None
        self.data = None
        self.plugins = []
        self.user = None

        weather_tool = weather_tool_factory()
        self.tools: list[dict] = [weather_tool]
        self.available_functions = {
            "get_current_weather": get_current_weather,
        }

    def validate(self):

        if not self.chat:
            raise ValueError(f"{self.formatted_class_name}: chat object is required")
        if not self.data:
            raise ValueError(f"{self.formatted_class_name}: data object is required")
        if not self.user:
            raise ValueError(f"{self.formatted_class_name}: user object is required")
        if not self.default_model:
            raise ValueError(f"{self.formatted_class_name}: default_model is required")
        if not self.default_system_role:
            raise ValueError(f"{self.formatted_class_name}: default_system_role is required")
        if not self.default_temperature:
            raise ValueError(f"{self.formatted_class_name}: default_temperature is required")
        if not self.default_max_tokens:
            raise ValueError(f"{self.formatted_class_name}: default_max_tokens is required")

        if self.default_model not in self.valid_chat_completion_models:
            raise ValueError(
                f"Internal error. Invalid default model: {self.default_model} not found in list of valid {self.name} models {self.valid_chat_completion_models}."
            )

    @property
    def messages(self) -> List[Dict[str, str]]:
        return self._messages

    def append_message(self, role: str, message: str) -> None:
        if role not in OpenAIMessageKeys.all_roles:
            raise SmarterValueError(
                f"Internal error. Invalid message role: {role} not found in list of valid {self.name} message roles {OpenAIMessageKeys.all_roles}."
            )
        if not message:
            # nothing to append
            return

        self._messages.append(
            {OpenAIMessageKeys.MESSAGE_ROLE_KEY: role, OpenAIMessageKeys.MESSAGE_CONTENT_KEY: message}
        )

    def append_message_plugin_selected(self, plugin: str) -> None:
        self.append_message(OpenAIMessageKeys.SMARTER_MESSAGE_KEY, f"Smarter selected this plugin: {plugin}")

    def append_message_tool_called(self, function_name: str, function_args: str) -> None:
        message = f"{self.name} called this tool: {function_name}({function_args})"
        self.append_message(OpenAIMessageKeys.SMARTER_MESSAGE_KEY, message)

    def prep_first_completion_request(
        self,
        messages: list[dict],
        model: str,
        tools: List[dict],
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ):
        self.first_iteration[InternalKeys.REQUEST_KEY] = {
            "model": model,
            InternalKeys.MESSAGES_KEY: messages,
            InternalKeys.TOOLS_KEY: self.tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # create a Smarter UI message with the established configuration
        message = f"Prompt configuration: llm={self.name}, model={model}, temperature={temperature}, max_tokens={max_tokens}, tool_choice={tool_choice}."
        self.append_message(OpenAIMessageKeys.SMARTER_MESSAGE_KEY, message)

        # for any tools that are included in the request, add Smarter UI messages for each tool
        if tools:
            for tool in tools:
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
                message = f"Tool presented: {tool_name}({inputs}) - {tool_description} "
                self.append_message(OpenAIMessageKeys.SMARTER_MESSAGE_KEY, message)

        # send a chat completion request signal. this triggers a variety of db records to be created
        # asynchronously in the background via Celery tasks.
        chat_completion_request.send(
            sender=self.handler,
            chat=self.chat,
            iteration=self.iteration,
            request=self.first_iteration[InternalKeys.REQUEST_KEY],
        )

    def handle_prompt_completion_response(self, model: str) -> None:
        """
        handle internal billing, and append messages to the response for prompt completion and the billing summary

        """
        user_id = self.user.id
        completion_tokens = (self.second_response.usage.completion_tokens,)
        prompt_tokens = (self.second_response.usage.prompt_tokens,)
        total_tokens = (self.second_response.usage.total_tokens,)
        system_fingerprint = (self.second_response.system_fingerprint,)
        response_message_role = (self.second_response.choices[0].message.role,)
        response_message_content = (self.second_response.choices[0].message.content,)

        chat_completion_response.send(
            sender=self.handler,
            chat=self.chat,
            iteration=self.iteration,
            request=self.second_iteration[InternalKeys.REQUEST_KEY],
            response=self.second_iteration[InternalKeys.RESPONSE_KEY],
        )

        logger.info("%s %s", self.formatted_class_name, formatted_text("handle_prompt_completion_response()"))
        create_prompt_completion_charge.delay(
            user_id, model, completion_tokens, prompt_tokens, total_tokens, system_fingerprint
        )
        self.append_message(
            role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY,
            message=f"{self.name} prompt charges: {prompt_tokens} prompt tokens, {completion_tokens} completion tokens = {total_tokens} total tokens charged.",
        )
        self.append_message(role=response_message_role, message=response_message_content)

    def handle_prompt_completion_plugin(self, model: str) -> None:
        logger.info("%s %s", self.formatted_class_name, formatted_text("handle_prompt_completion_plugin()"))
        create_plugin_charge.delay(
            user_id=self.user.id,
            model=model,
            completion_tokens=self.second_response.usage.completion_tokens,
            prompt_tokens=self.second_response.usage.prompt_tokens,
            total_tokens=self.second_response.usage.total_tokens,
            fingerprint=self.second_response.system_fingerprint,
        )

    @property
    def formatted_class_name(self):
        return formatted_text(self.__class__.__name__)

    @property
    def name(self) -> str:
        return self._name

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

    def get_message_thread(self, data: dict) -> List[Dict[str, str]]:
        default_system_role = self.chat.chatbot.default_system_role or self.default_system_role
        request_body = get_request_body(data=data)
        messages, _ = parse_request(request_body)
        messages = ensure_system_role_present(messages=messages, default_system_role=default_system_role)
        messages = clean_messages(messages=messages)
        return messages

    def get_input_text_prompt(self, data: dict) -> str:
        request_body = get_request_body(data=data)
        _, input_text = parse_request(request_body)
        return input_text

    def prepare_tool_call(self, tool_call) -> dict:
        """
        tool_call: List[ChatCompletionMessageToolCall]
        """
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
        elif function_name.startswith("function_calling_plugin"):
            # FIX NOTE: we should revisit this. technically, we're supposed to be calling
            # function_to_call, assigned above. but just to play it safe,
            # we're directly invoking the plugin's function_calling_plugin() method.
            plugin_id = int(function_name[-4:])
            plugin = PluginStatic(plugin_id=plugin_id)
            plugin.params = function_args
            function_response = plugin.function_calling_plugin(inquiry_type=function_args.get("inquiry_type"))
            serialized_tool_call["smarter_plugin"] = PluginMetaSerializer(plugin.plugin_meta).data
        tool_call_message = {
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": function_name,
            "content": function_response,
        }
        return tool_call_message, serialized_tool_call

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
            default_model: Default model to use for the chat completion example: "gpt-4-turbo"
            default_temperature: Default temperature to use for the chat completion example: 0.5
            default_max_tokens: Default max tokens to use for the chat completion example: 256

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
        self.chat = chat
        self.data = data
        self.plugins = plugins
        self.user = user

        self.validate()
        self.iteration = 1
        openai.api_key = self.api_key
        openai.base_url = self.base_url
        model = self.chat.chatbot.default_model or self.default_model
        temperature = self.chat.chatbot.default_temperature or self.default_temperature
        max_tokens = self.chat.chatbot.default_max_tokens or self.default_max_tokens

        try:
            messages = self.get_message_thread(data=self.data)
            input_text = self.get_input_text_prompt(data=self.data)
            request_meta_data = request_meta_data_factory(model, temperature, max_tokens, input_text)
            chat_invocation_start.send(sender=self.handler, chat=self.chat, data=self.data)

            # does the prompt have anything to do with any of the search terms defined in a plugin?
            # FIX NOTE: need to decide on how to resolve which of many plugin values sets to use for model, temperature, max_tokens
            logger.warning(
                "smarter.apps.chat.providers.base_classes.OpenAICompatibleChatProvider.handler(): plugins selector needs to be refactored to use Django model."
            )
            for plugin in self.plugins:
                if plugin.selected(user=self.user, input_text=input_text):
                    model = plugin.plugin_prompt.model
                    temperature = plugin.plugin_prompt.temperature
                    max_tokens = plugin.plugin_prompt.max_tokens
                    messages = plugin.customize_prompt(messages)
                    custom_tool = plugin.custom_tool
                    self.tools.append(custom_tool)
                    self.available_functions[plugin.function_calling_identifier] = plugin.function_calling_plugin
                    self.append_message_plugin_selected(plugin=plugin.plugin_meta.name)

            self.prep_first_completion_request(
                messages=messages,
                model=model,
                tools=self.tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
            )

            self.first_response = openai.chat.completions.create(
                model=model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # serialize the response and then convert to json. this deconstructs the
            # response from openai Python objects into pure json.
            first_response_dict = json.loads(self.first_response.model_dump_json())
            self.first_iteration[InternalKeys.RESPONSE_KEY] = first_response_dict
            self.handle_prompt_completion_response(model=model)
            response_message = self.first_response.choices[0].message
            tool_calls: list[ChatCompletionMessageToolCall] = response_message.tool_calls
            if tool_calls:
                self.iteration = 2
                second_request_messages = messages.copy()
                second_request_messages = clean_messages(messages=second_request_messages)
                # this is intended to force a json serialization exception
                # in the event that we've neglected to properly serialize all
                # responses from openai api.
                response_message_serialized = response_message.model_dump_json()
                second_request_messages_serialized: list[dict] = json.loads(json.dumps(second_request_messages))
                second_request_messages_serialized.append(response_message_serialized)
                self.serialized_tool_calls = []

                # Step 3: call the function
                # Note: the JSON response may not always be valid; be sure to handle errors
                second_request_messages.append(response_message)  # extend conversation with assistant's reply

                # Step 4: send the info for each function call and function response to the model

                for tool_call in tool_calls:
                    tool_call_message, serialized_tool_call = self.prepare_tool_call(tool_call)
                    second_request_messages.append(tool_call_message)  # extend conversation with function response
                    second_request_messages_serialized.append(tool_call_message)
                    self.serialized_tool_calls.append(serialized_tool_call)

                self.second_iteration[InternalKeys.REQUEST_KEY] = {
                    "model": model,
                    InternalKeys.MESSAGES_KEY: second_request_messages_serialized,
                }
                chat_completion_request.send(
                    sender=self.handler,
                    chat=self.chat,
                    iteration=self.iteration,
                    request=self.second_iteration[InternalKeys.REQUEST_KEY],
                )
                self.second_response = openai.chat.completions.create(
                    model=model,
                    messages=second_request_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )  # get a new response from the model where it can see the function response
                self.second_response_dict = json.loads(self.second_response.model_dump_json())
                self.second_iteration[InternalKeys.RESPONSE_KEY] = self.second_response_dict
                self.second_iteration[InternalKeys.REQUEST_KEY][
                    InternalKeys.MESSAGES_KEY
                ] = second_request_messages_serialized
                self.handle_prompt_completion_response(model=model)
                chat_completion_tool_called.send(
                    sender=self.handler,
                    chat=self.chat,
                    tool_calls=self.serialized_tool_calls,
                    request=self.second_iteration[InternalKeys.REQUEST_KEY],
                    response=self.second_iteration[InternalKeys.RESPONSE_KEY],
                )
                self.handle_prompt_completion_plugin(model=model)

        # handle anything that went wrong
        # pylint: disable=broad-exception-caught
        except Exception as e:
            chat_response_failure.send(
                sender=self.handler,
                iteration=self.iteration,
                chat=self.chat,
                request_meta_data=self.request_meta_data,
                exception=e,
                first_response=first_response_dict,
                second_response=self.second_response_dict,
            )
            status_code, _message = EXCEPTION_MAP.get(
                type(e), (HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
            )
            return http_response_factory(
                status_code=status_code,
                body=exception_response_factory(exception=e, request_meta_data=self.request_meta_data),
            )

        # success!! return the response
        response = self.second_iteration.get(InternalKeys.RESPONSE_KEY) or self.first_iteration.get(
            InternalKeys.RESPONSE_KEY
        )
        response["metadata"] = {"tool_calls": self.serialized_tool_calls, **request_meta_data}

        response[OpenAIMessageKeys.SMARTER_MESSAGE_KEY] = {
            "first_iteration": json.loads(json.dumps(self.first_iteration)),
            "second_iteration": json.loads(json.dumps(self.second_iteration)),
            InternalKeys.TOOLS_KEY: [tool["function"]["name"] for tool in self.tools],
            InternalKeys.PLUGINS_KEY: [plugin.plugin_meta.name for plugin in self.plugins],
            InternalKeys.MESSAGES_KEY: self.messages,
        }
        chat_invocation_finished.send(
            sender=self.handler,
            chat=self.chat,
            request=self.first_iteration.get(InternalKeys.REQUEST_KEY),
            response=response,
        )
        return http_response_factory(status_code=HTTPStatus.OK, body=response)
