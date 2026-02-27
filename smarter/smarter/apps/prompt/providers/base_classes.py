# pylint: disable=C0302
"""
Base class for chat providers.
"""

import logging
import traceback
from functools import cached_property
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Protocol, Union

import openai

# 3rd party stuff
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallUnion,
)

from smarter.apps.account.models import (
    CHARGE_TYPE_PLUGIN,
    CHARGE_TYPE_PROMPT_COMPLETION,
    CHARGE_TYPE_TOOL,
    User,
)
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginMeta
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
from smarter.apps.prompt.models import Chat

# smarter chat provider stuff
from smarter.apps.prompt.providers.utils import (
    ensure_system_role_present,
    exception_response_factory,
    get_request_body,
    http_response_factory,
    parse_request,
)
from smarter.apps.prompt.receivers import (
    llm_tool_presented,
    llm_tool_requested,
    llm_tool_responded,
)
from smarter.apps.prompt.signals import (
    chat_completion_plugin_called,
    chat_completion_request,
    chat_completion_response,
    chat_completion_tool_called,
    chat_finished,
    chat_provider_initialized,
    chat_response_failure,
    chat_started,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import (
    SmarterConfigurationError,
    SmarterIlligalInvocationError,
    SmarterValueError,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.helpers.llm import get_date_time_string
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .const import OpenAIMessageKeys
from .mixins import ProviderDbMixin


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

# 1.) EXCEPTION_MAP: A dictionary that maps exceptions to HTTP status codes and error types.
# Base exception map for chat providers. This maps internally raised exceptions to HTTP status codes.
BASE_EXCEPTION_MAP = {
    SmarterValueError: (HTTPStatus.BAD_REQUEST.value, "BadRequest"),
    SmarterConfigurationError: (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError"),
    SmarterIlligalInvocationError: (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError"),
    ValueError: (HTTPStatus.BAD_REQUEST.value, "BadRequest"),
    TypeError: (HTTPStatus.BAD_REQUEST.value, "BadRequest"),
    NotImplementedError: (HTTPStatus.BAD_REQUEST.value, "BadRequest"),
    Exception: (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError"),
}

EXCEPTION_MAP = BASE_EXCEPTION_MAP.copy()
EXCEPTION_MAP[openai.APIError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
EXCEPTION_MAP[openai.OpenAIError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.ConflictError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.NotFoundError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.APIStatusError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.RateLimitError] = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "InternalServerError")
EXCEPTION_MAP[openai.APITimeoutError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.BadRequestError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
EXCEPTION_MAP[openai.APIConnectionError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.AuthenticationError] = (HTTPStatus.UNAUTHORIZED.value, "UnauthorizedError")
EXCEPTION_MAP[openai.InternalServerError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.PermissionDeniedError] = (HTTPStatus.UNAUTHORIZED.value, "UnauthorizedError")
EXCEPTION_MAP[openai.LengthFinishReasonError] = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "RequestEntityTooLargeError")
EXCEPTION_MAP[openai.UnprocessableEntityError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
EXCEPTION_MAP[openai.APIResponseValidationError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
EXCEPTION_MAP[openai.ContentFilterFinishReasonError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
"""
Used in the main try block of handler() to map exceptions to HTTP status codes and error types.
"""

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
    API_URL = "api_url"
    API_KEY = "api_key"
    TEMPERATURE_KEY = "temperature"
    MAX_COMPLETION_TOKENS_KEY = "max_completion_tokens"
    TOOL_CHOICE = "tool_choice"

    SMARTER_PLUGIN_KEY = SMARTER_SYSTEM_KEY_PREFIX + "plugin"
    SMARTER_IS_NEW = SMARTER_SYSTEM_KEY_PREFIX + "is_new"


class HandlerProtocol(Protocol):
    """
    A fixed Protocol for all chat provider handler functions.
    Ensures that all handler functions have exactly the same signature.

    :param user: The user making the request.
    :type user: User
    :param chat: The chat object.
    :type chat: Chat
    :param data: The request data.
    :type data: Union[dict[str, Any], list]
    :param plugins: Optional list of plugins to use.
    :type plugins: Optional[List[PluginBase]]
    :param functions: Optional list of function names to use.
    :type functions: Optional[list[str]]

    :returns: The response data.
    :rtype: Union[dict[str, Any], list]
    """

    def __call__(
        self,
        user: User,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> Union[dict[str, Any], list]: ...


class ChatProviderBase(ProviderDbMixin):
    """
    Base class for all chat providers.
    """

    __slots__ = (
        "_provider",
        "_default_model",
        "_default_system_role",
        "_default_temperature",
        "_default_max_completion_tokens",
        "_valid_chat_completion_models",
        "_messages",
        "_base_url",
        "_api_key",
        "_chat",
        "data",
        "plugins",
        "functions",
        "model",
        "temperature",
        "max_completion_tokens",
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

    _provider: Optional[str]
    _default_model: Optional[str]
    _default_system_role: Optional[str]
    _default_temperature: Optional[float]
    _default_max_completion_tokens: Optional[int]

    _valid_chat_completion_models: Optional[list[str]]
    _messages: Optional[List[Dict[str, str]]]

    _base_url: Optional[str]
    _api_key: Optional[str]
    _chat: Optional[Chat]

    data: Optional[dict[str, Any]]
    plugins: List[PluginBase]
    functions: Optional[List[str]]

    model: Optional[str]
    temperature: Optional[float]
    max_completion_tokens: Optional[int]
    input_text: Optional[str]

    completion_tokens: Optional[int]
    prompt_tokens: Optional[int]
    total_tokens: Optional[int]
    reference: Optional[str]

    iteration: int
    request_meta_data: dict[str, Any]
    first_iteration: dict[str, Any]
    first_response: Optional[ChatCompletion]
    second_response: Optional[ChatCompletion]
    second_iteration: Optional[dict[str, Any]]
    serialized_tool_calls: Optional[list[dict[str, Any]]]

    # built-in tools that we make available to all providers
    tools: Optional[list[dict[str, Any]]]
    available_functions: dict[str, Any]

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

        # constructor arguments
        self._default_model = None
        self._default_system_role = None
        self._default_temperature = None
        self._default_max_completion_tokens = None

        self._valid_chat_completion_models = None
        self._messages = []

        self._base_url = None
        self._api_key = None

        self._chat = None
        self.data = None
        self.plugins = None
        self.functions = None

        self.model = None
        self.temperature = None
        self.max_completion_tokens = None
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

        # initializations
        self.serialized_tool_calls = None
        self._chat = kwargs.get("chat")
        self._provider = provider
        self._base_url = base_url
        self._api_key = api_key

        self._default_model = default_model
        self._default_system_role = default_system_role
        self._default_temperature = default_temperature
        self._default_max_completion_tokens = default_max_tokens
        self._valid_chat_completion_models = valid_chat_completion_models

        weather_tool = weather_tool_factory()
        date_calculator_tool = date_calculator_tool_factory()
        self.tools = [weather_tool, date_calculator_tool] if add_built_in_tools else None
        self.available_functions = (
            {
                get_current_weather.__name__: get_current_weather,
                date_calculator.__name__: date_calculator,
                calculator.__name__: calculator,
            }
            if add_built_in_tools
            else {}
        )

        chat_provider_initialized.send(sender=self)

    def prune_empty_values(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Remove empty values from a dictionary. Some
        LLM providers, including MetaAI and GoogleAI
        will break if empty values are present in the
        completion request body.
        """
        if not isinstance(data, dict):
            raise SmarterValueError(f"{self.formatted_class_name}: data must be a dictionary")

        def _prune(obj: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
            if isinstance(obj, dict):
                return {k: _prune(v) for k, v in obj.items() if v is not None}
            elif isinstance(obj, list):
                return [_prune(item) for item in obj if item is not None]
            else:
                return obj

        return _prune(data)

    def validate(self):
        """
        Validate that all required properties are set. Raise
        SmarterValueError if any required property is missing.

        :raises SmarterValueError: If any required property is missing.

        :returns: None
        :rtype: None
        """
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

        if self.valid_chat_completion_models and self.default_model not in self.valid_chat_completion_models:
            raise SmarterValueError(
                f"Internal error. Invalid default model: {self.default_model} not found in list of valid {self.provider} models {self.valid_chat_completion_models}."
            )

        if not self.account:
            self.account = self.chat.account

    @cached_property
    def ready(self) -> bool:
        """
        Check if the chat provider is ready to process requests.

        :returns: True if the chat provider is ready, False otherwise.
        :rtype: bool
        """
        return bool(self.chat) and bool(self.data) and bool(self.account)

    @property
    def messages(self) -> Optional[List[Dict[str, str]]]:
        """
        Get the list of messages in the chat. This property
        returns the internal _messages attribute.

        :returns: The list of messages.
        :rtype: Optional[List[Dict[str, str]]]
        """
        return self._messages

    @messages.setter
    def messages(self, value: List[Dict[str, str]]) -> None:
        """
        Set the list of messages in the chat. This property
        sets the internal _messages attribute.

        :param value: The list of messages to set.
        :type value: List[Dict[str, str]]

        :returns: None
        :rtype: None
        """
        self._messages = value

    @cached_property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.

        :returns: The formatted class name.
        :rtype: str
        """
        return f"{__name__}.{ChatProviderBase.__name__}[{id(self)}]"

    @property
    def provider(self) -> Optional[str]:
        """
        Get the name of the chat provider. This property
        returns the internal _provider attribute.

        :returns: The name of the chat provider.
        :rtype: Optional[str]
        """
        return self._provider

    @property
    def base_url(self) -> Optional[str]:
        """
        Get the base URL of the chat provider. This property
        returns the internal _base_url attribute.

        :returns: The base URL of the chat provider.
        :rtype: Optional[str]
        """
        return self._base_url

    @property
    def url(self) -> Optional[str]:
        """
        Get the full URL for chat completions. This property
        constructs the URL by appending the chat completions
        endpoint to the base URL.

        :examples:

            If the base URL is "https://api.some-llm-company.com", the full URL will be
            "https://api.some-llm-company.com/v1/chat/completions".

        :returns: The full URL for chat completions.
        :rtype: Optional[str]
        """
        return self._base_url + "chat/completions" if self._base_url else None

    @property
    def api_key(self) -> Optional[str]:
        """
        Get the API key of the chat provider. This property
        returns the unmasked internal _api_key attribute.

        :returns: The unmasked API key of the chat provider.
        :rtype: Optional[str]
        """
        return self._api_key

    @property
    def default_model(self) -> Optional[str]:
        """
        Get the default model of the chat provider. This property
        returns the internal _default_model attribute.

        :returns: The default model of the chat provider.
        :rtype: Optional[str]
        """
        return self._default_model

    @property
    def default_system_role(self) -> Optional[str]:
        """
        Get the default system role of the chat provider. This property
        returns the internal _default_system_role attribute.

        :returns: The default system role of the chat provider.
        :rtype: Optional[str]
        """
        return self._default_system_role

    @property
    def default_temperature(self) -> Optional[float]:
        """
        Get the default temperature of the chat provider. This property
        returns the internal _default_temperature attribute.

        :returns: The default temperature of the chat provider.
        :rtype: Optional[float]
        """
        return self._default_temperature

    @property
    def default_max_tokens(self) -> Optional[int]:
        """
        Get the default max completion tokens of the chat provider. This property
        returns the internal _default_max_completion_tokens attribute.

        :returns: The default max completion tokens of the chat provider.
        :rtype: Optional[int]
        """
        return self._default_max_completion_tokens

    @property
    def valid_chat_completion_models(self) -> Optional[list[str]]:
        """
        Get the list of valid chat completion models for the chat provider. This property
        returns the internal _valid_chat_completion_models attribute.

        A valid chat completion model is one that is supported by the chat provider's
        API for chat completions.

        :returns: The list of valid chat completion models.
        :rtype: Optional[list[str]]
        """
        return self._valid_chat_completion_models

    def messages_set_is_new(self, messages: list[dict[str, Any]], is_new: bool = False) -> list[dict[str, Any]]:
        """
        Set the is_new flag for all messages in the message thread. This is used to
        track which messages are new and which have already been processed.

        This affects the treatment of messages in the Reactapp component, where new messages
        are styled differently.

        :param messages: The list of messages to set the is_new flag for.
        :type messages: list[dict[str, Any]]
        """
        retval = []
        for message in messages:
            new_message = message.copy()
            new_message[InternalKeys.SMARTER_IS_NEW] = is_new
            retval.append(new_message)
        return retval

    def get_message_thread(self, data: dict[str, Any]) -> List[Dict[str, str]]:
        """
        Initialize a new message thread with a system prompt
        and the incoming data. This method ensures that the system
        role is present in the message thread.

        :raises SmarterValueError: If the request body is invalid.

        :param data: The incoming data containing the message thread.
        :type data: dict[str, Any]
        :returns: The initialized message thread.
        :rtype: List[Dict[str, str]]
        """
        default_system_role = get_date_time_string()
        if self.chat and self.chat.chatbot and self.chat.chatbot.default_system_role_enhanced:
            default_system_role += self.chat.chatbot.default_system_role_enhanced
        request_body = get_request_body(data=data)
        client_message_thread, _ = parse_request(request_body)
        if not isinstance(client_message_thread, list):
            raise SmarterValueError(
                f"{self.formatted_class_name}: Invalid request body. Expected a list of messages, got: {type(client_message_thread)}"
            )
        client_message_thread = ensure_system_role_present(
            messages=client_message_thread, default_system_role=default_system_role
        )
        retval = self.messages_set_is_new(client_message_thread, is_new=False)
        return retval

    def get_input_text_prompt(self, data: dict[str, Any]) -> str:
        """
        Extract the input text prompt from the incoming data. This method
        validates that the input text is present and is a string.

        :raises SmarterValueError: If the input text is missing or invalid.

        :param data: The incoming data containing the input text.
        :type data: dict[str, Any]
        :returns: The input text prompt.
        :rtype: str
        """
        request_body = get_request_body(data=data)
        _, input_text = parse_request(request_body)
        if not input_text:
            raise SmarterValueError(f"{self.formatted_class_name}: input_text is required")
        if not isinstance(input_text, str):
            raise SmarterValueError(f"{self.formatted_class_name}: input_text must be a string")
        return input_text

    def append_message(
        self, role: str, content: Optional[Union[dict[str, Any], list, str]], message: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Append a message to the internal message list. This method
        validates the role and content before appending the message.

        :param role: The role of the message (e.g., "user", "assistant", "system").
        :type role: str

        :param content: The content of the message. Can be a string, dict[str, Any], or list.
        :type content: Optional[Union[dict[str, Any], list, str]]

        :param message: An optional message dictionary to append. If provided,
            it will be used instead of creating a new message.

        :raises SmarterValueError: If the role is invalid or if both content and message are empty.

        :returns: None
        :rtype: None

        """
        if role not in OpenAIMessageKeys.all_roles:
            raise SmarterValueError(
                f"Internal error. Invalid message role: {role} not found in list of valid {self.provider} message roles {OpenAIMessageKeys.all_roles}."
            )
        if not content and not message:
            raise SmarterValueError(
                f"{self.formatted_class_name}: content or message must be provided. Both cannot be empty."
            )
        message = message or {}
        if not isinstance(message, dict):
            raise SmarterValueError(f"{self.formatted_class_name}: message must be a dictionary")
        new_message = message.copy()
        new_message[OpenAIMessageKeys.MESSAGE_ROLE_KEY] = role
        new_message[OpenAIMessageKeys.MESSAGE_CONTENT_KEY] = content
        new_message[InternalKeys.SMARTER_IS_NEW] = True
        if isinstance(self.messages, list):
            self.messages.append(new_message)

    def append_message_plugin_selected(self, plugin: str) -> None:
        """
        Append a message indicating that a plugin was selected.

        :param plugin: The name of the selected plugin.
        :type plugin: str
        :returns: None
        :rtype: None
        """
        content = f"Smarter selected this plugin: {plugin}"
        self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

    def append_message_tool_called(self, tool_call: ChatCompletionMessageToolCallUnion) -> None:
        """
        Append a message indicating that a tool was called.

        :param tool_call: The tool call object containing function name and arguments.
        :type tool_call: ChatCompletionMessageToolCallUnion
        :returns: None
        :rtype: None
        """
        tool_call_to_json = tool_call.model_dump()
        content = f"{self.provider} called this tool: {tool_call.function.name}({tool_call.function.arguments})"
        content = content + f"\n\nTool call:\n--------------------\n{json.dumps(tool_call_to_json, indent=4)}"
        self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

    def _insert_charge_by_type(self, charge_type: str) -> None:
        """
        Insert a charge record based on the charge type. This method
        uses the internal db_insert_charge method to create a charge
        record in the database.

        :param charge_type: The type of charge (e.g., prompt completion, tool, plugin).
        :type charge_type: str

        :returns: None
        :rtype: None
        """
        self.db_insert_charge(
            provider=self.provider,
            charge_type=charge_type,
            completion_tokens=self.completion_tokens,
            prompt_tokens=self.prompt_tokens,
            total_tokens=self.total_tokens,
            model=self.model,
            reference=self.reference or "ChatProviderBase._insert_charge_by_type()",
        )


class OpenAICompatibleChatProvider(ChatProviderBase):
    """
    A chat provider that works with any vendor provider that is
    fully compatible with OpenAI's text completion API.
    """

    @property
    def openai_messages(self) -> list[dict[str, Any]]:
        """
        Return a sanitized list of messages compatible with OpenAI's chat completion API.

        This property processes the internal message list, removing Smarter-specific annotations
        (such as metadata about tool calls and interim completion token charges) to ensure that
        only valid OpenAI message fields are included. This is essential for avoiding API errors
        related to unexpected or extraneous fields.

        :returns: A list of dictionaries representing chat messages, formatted for OpenAI's API.
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

            - https://platform.openai.com/docs/api-reference/chat/create
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
            if InternalKeys.SMARTER_IS_NEW in message_copy:
                del message_copy[InternalKeys.SMARTER_IS_NEW]
            retval.append(message_copy)
        return retval

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
            return [message for message in self.messages if message[InternalKeys.SMARTER_IS_NEW]]
        except KeyError:
            prefix = formatted_text(f"{self.formatted_class_name} new_messages()")
            logger.error(
                "%s - KeyError: '%s' key not found in message: %s", prefix, InternalKeys.SMARTER_IS_NEW, self.messages
            )
        return self.messages

    def prep_first_request(self):
        """
        Prepare the first request for the chat completion. This is called
        at the beginning of the chat completion process.

        :raises SmarterValueError: If the messages are not a list, or if tool definitions are invalid.

        :returns: None
        :rtype: None
        """
        logger.debug("%s %s", self.formatted_class_name, formatted_text("prep_first_request()"))
        # ensure that all message history is marked as not new
        if isinstance(self.messages, list):
            self.messages = self.messages_set_is_new(self.messages, is_new=False)
        tool_choice = OPENAI_TOOL_CHOICE
        self.first_iteration[InternalKeys.REQUEST_KEY] = {
            InternalKeys.API_URL: self.base_url,
            InternalKeys.API_KEY: self.mask_string(self.api_key),
            InternalKeys.MODEL_KEY: self.model,
            InternalKeys.MESSAGES_KEY: self.openai_messages,
            InternalKeys.TEMPERATURE_KEY: self.temperature,
            InternalKeys.MAX_COMPLETION_TOKENS_KEY: self.max_completion_tokens,
            InternalKeys.TOOLS_KEY: self.tools,
        }

        # create a Smarter UI message with the established configuration
        content = f"Prompt configuration: llm={self.provider}, url={self.url} api_key={self.mask_string(self.api_key)} model={self.model}, temperature={self.temperature}, max_completion_tokens={self.max_completion_tokens}"
        if self.tools:
            content = content + f", tool_choice={tool_choice}."
        self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

        if self.tools:
            # this is necessary because of this 400 response in cases where
            # tool_choice is set but not tools are provided:
            # 'Error code: 400 - Invalid value 'tool_choice' is only allowed when 'tools' are specified."
            #
            # pylint: disable=E1137
            self.first_iteration[InternalKeys.REQUEST_KEY][InternalKeys.TOOL_CHOICE] = tool_choice

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

        # send a chat completion request signal. this triggers a variety of db records to be created
        # asynchronously in the background via Celery tasks.
        chat_completion_request.send(
            sender=self.handler,
            chat=self.chat,
            iteration=self.iteration,
            request=self.first_iteration[InternalKeys.REQUEST_KEY],
        )

    def prep_second_request(self):
        """
        Prepare the second request for the chat completion. This is called
        in response to a tool call that requires a second request to the LLM.

        :returns: None
        :rtype: None
        """
        logger.debug("%s.prep_second_request() called.", self.formatted_class_name)
        if not isinstance(self.second_iteration, dict):
            raise SmarterValueError(
                f"{self.formatted_class_name}: second_iteration must be a dictionary, got {type(self.second_iteration)}"
            )
        self.second_iteration[InternalKeys.REQUEST_KEY] = {
            InternalKeys.API_URL: self.base_url,
            InternalKeys.API_KEY: self.mask_string(self.api_key),
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
        """
        Append the OpenAI-compatible response message to the internal message list.
        2025-06-20: updated to use model_dump_json() to ensure compatibility with Pydantic v2.
        2025-10-02: updated to validate that the response message is indeed a ChatCompletionMessage.

        :param response: The OpenAI-compatible chat completion response.
        :type response: ChatCompletion

        :returns: None
        :rtype: None
        """
        logger.debug("%s.append_openai_response() called.", self.formatted_class_name)
        response_message = response.choices[0].message
        message_json = json.loads(response_message.model_dump_json())
        if not isinstance(response_message, ChatCompletionMessage):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}: response_message or response_message.content is empty. Response: {response.model_dump_json()}"
            )
        self.append_message(role=response_message.role, content=response_message.content, message=message_json)  # type: ignore[call-arg]

    def handle_response(self) -> None:
        """
        handle internal billing, and append messages to the response for prompt completion and the billing summary

        :returns: None
        :rtype: None
        """
        logger.debug(
            "%s %s", self.formatted_class_name, formatted_text(f"handle_response() iteration: {self.iteration}")
        )

        response = self.second_response if self.iteration == 2 else self.first_response
        if not response:
            raise SmarterValueError(
                f"{self.formatted_class_name}: response is required for iteration {self.iteration}, but was not set."
            )
        if not response.usage:
            raise SmarterValueError(
                f"{self.formatted_class_name}: response.usage is required for iteration {self.iteration}, but was not set."
            )
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
            if not self.first_response:
                raise SmarterIlligalInvocationError(
                    f"{self.formatted_class_name}: first_response is required for iteration 1, but was not set."
                )
            self.first_iteration[InternalKeys.RESPONSE_KEY] = json.loads(self.first_response.model_dump_json())
        if self.iteration == 2:
            if not self.second_response:
                raise SmarterIlligalInvocationError(
                    f"{self.formatted_class_name}: second_response is required for iteration 2, but was not set."
                )
            if not isinstance(self.second_iteration, dict):
                raise SmarterValueError(
                    f"{self.formatted_class_name}: second_iteration must be a dictionary, got {type(self.second_iteration)}"
                )
            self.second_iteration[InternalKeys.RESPONSE_KEY] = json.loads(self.second_response.model_dump_json())

        serialized_request = (
            self.first_iteration[InternalKeys.REQUEST_KEY]
            if self.iteration == 1
            else self.second_iteration[InternalKeys.REQUEST_KEY] if self.second_iteration else None
        )
        serialized_response = (
            self.first_iteration[InternalKeys.RESPONSE_KEY]
            if self.iteration == 1
            else self.second_iteration[InternalKeys.RESPONSE_KEY] if self.second_iteration else None
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

        :param function_name: The name of the tool function called.
        :type function_name: str
        :param function_args: The arguments passed to the tool function.
        :type function_args: str

        :returns: None
        :rtype: None
        """
        logger.debug("%s %s - %s", self.formatted_class_name, formatted_text("handle_tool_called()"), function_name)
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

    def handle_plugin_called(self, plugin: PluginBase) -> None:
        """
        handle a plugin tool call. example: SqlPlugin, ApiPlugin, StaticPlugin etc.

        :param plugin: The plugin instance that was called.
        :type plugin: PluginBase

        :returns: None
        :rtype: None
        """
        logger.debug("%s %s - %s", self.formatted_class_name, formatted_text("handle_plugin_called()"), plugin.name)
        chat_completion_plugin_called.send(
            sender=self.handler,
            chat=self.chat,
            plugin=plugin,
            input_text=self.input_text,
        )
        self._insert_charge_by_type(CHARGE_TYPE_PLUGIN)
        self.db_insert_chat_plugin_usage(chat=self.chat, plugin=plugin, input_text=self.input_text)

    def process_tool_call(self, tool_call: ChatCompletionMessageToolCallUnion):
        """
        Process a tool call from the LLM. This method handles both built-in tool calls
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
        if function_name in [get_current_weather.__name__, date_calculator.__name__, calculator.__name__]:
            function_response = function_to_call(tool_call=tool_call)
            self.handle_tool_called(function_name=function_name, function_args=function_args)

        elif function_name.startswith(smarter_settings.function_calling_identifier_prefix):
            plugin_id = int(function_name[-4:])
            try:
                plugin_meta = PluginMeta.objects.get(id=plugin_id)
            except PluginMeta.DoesNotExist as e:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: plugin with id {plugin_id} not found. This is a bug."
                ) from e

            if not self.account:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: account is required to handle plugin calls."
                )
            if not self.user:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: user is required to handle plugin calls."
                )
            if not self.user_profile:
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: user_profile is required to handle plugin calls."
                )
            if not isinstance(self.user, User):
                raise SmarterConfigurationError(
                    f"{self.formatted_class_name}: user must be an instance of User, got {type(self.user)}. This is a bug."
                )
            plugin_controller = PluginController(
                account=self.account,
                user=self.user,
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
            serialized_tool_call[InternalKeys.SMARTER_PLUGIN_KEY] = PluginMetaSerializer(plugin.plugin_meta).data
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
        llm_tool_responded.send(
            sender=self.process_tool_call, tool_call=tool_call.model_dump(), tool_response=function_response
        )

    def handle_plugin_selected(self, plugin: PluginBase) -> None:
        """
        Handle a plugin being selected.

        does the prompt have anything to do with any of the search terms defined in a plugin?
        TODO: need to decide on how to resolve which of many plugin values sets to use for model, temperature, max_completion_tokens
        2025-10-02: updated to validate that messages and tools are lists.
        2025-10-02: updated to use plugin.plugin_meta.name for the plugin name.

        :param plugin: The plugin instance that was selected.
        :type plugin: PluginBase

        :returns: None
        :rtype: None
        """
        logger.debug("%s.handle_plugin_selected() called.", self.formatted_class_name)
        logger.warning(
            "smarter.apps.prompt.providers.base_classes.OpenAICompatibleChatProvider.handler(): plugins selector needs to be refactored to use Django model."
        )
        if not isinstance(self.messages, list):
            raise SmarterValueError(f"{self.formatted_class_name}: messages must be a list, got {type(self.messages)}")
        self.model = plugin.plugin_prompt.model
        self.temperature = plugin.plugin_prompt.temperature
        self.max_completion_tokens = plugin.plugin_prompt.max_completion_tokens
        self.messages = plugin.customize_prompt(self.messages)
        if self.tools is None:
            self.tools = []
        self.tools.append(plugin.custom_tool)
        self.available_functions[plugin.function_calling_identifier] = plugin.tool_call_fetch_plugin_response
        self.append_message_plugin_selected(plugin=plugin.plugin_meta.name)  # type: ignore[call-arg]
        llm_tool_presented.send(sender=self.handle_plugin_selected, tool=plugin.custom_tool, plugin=plugin)
        # note to self: Plugin sends a plugin_selected signal, so no need to send it here.

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

    def handle_success(self) -> dict:
        """
        Handle a successful chat completion response. This method
        formats the final response to be returned to the client.

        :returns: A dictionary representing the final chat completion response.
        :rtype: dict
        """
        logger.debug("%s.handle_success() called", self.formatted_class_name)
        if not isinstance(self.second_iteration, dict):
            raise SmarterValueError(
                f"{self.formatted_class_name}: second_iteration must be a dictionary, got {type(self.second_iteration)}"
            )
        response = self.second_iteration.get(InternalKeys.RESPONSE_KEY) or self.first_iteration.get(
            InternalKeys.RESPONSE_KEY
        )
        if not isinstance(response, dict):
            raise SmarterValueError(f"{self.formatted_class_name}: response must be a dictionary, got {type(response)}")
        response["metadata"] = {"tool_calls": self.serialized_tool_calls, **self.request_meta_data}

        response[OpenAIMessageKeys.SMARTER_MESSAGE_KEY] = {
            "first_iteration": json.loads(json.dumps(self.first_iteration)),
            "second_iteration": json.loads(json.dumps(self.second_iteration)),
            InternalKeys.PLUGINS_KEY: [plugin.plugin_meta.name for plugin in self.plugins],  # type: ignore[call-arg]
            InternalKeys.MESSAGES_KEY: self.new_messages,
        }
        if self.tools:
            response_extended = response.get(OpenAIMessageKeys.SMARTER_MESSAGE_KEY).copy() or {}  # type: ignore[call-arg]
            response_extended[InternalKeys.TOOLS_KEY] = [tool["function"]["name"] for tool in self.tools]
            response[OpenAIMessageKeys.SMARTER_MESSAGE_KEY] = response_extended
        return response

    def request_meta_data_factory(self):
        """
        Return a dictionary of request meta data. This includes
        the model, temperature, max_completion_tokens, and input_text.

        :returns: A dictionary of request meta data.
        :rtype: dict
        """
        logger.debug("%s.request_meta_data_factory() called.", self.formatted_class_name)
        return {
            InternalKeys.MODEL_KEY: self.model,
            InternalKeys.TEMPERATURE_KEY: self.temperature,
            InternalKeys.MAX_COMPLETION_TOKENS_KEY: self.max_completion_tokens,
            "input_text": self.input_text,
        }

    def handler(
        self,
        user: User,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[list[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> Union[dict[str, Any], list]:
        """
        Process a chat prompt request and invoke the appropriate OpenAI-compatible API endpoint.

        This method orchestrates the entire chat completion workflow, including:

        - Validating input and internal state.
        - Initializing or updating the message thread.
        - Selecting and configuring plugins and/or functions (collectively, tool calls) for the LLM.
        - Preparing and sending requests to the OpenAI API (or compatible provider).
        - Handling tool calls and plugin responses.
        - Managing billing, logging, and signal dispatch.
        - Returning a formatted HTTP response with the LLM's output and relevant metadata.

        :param user: The user instance making the request.
        :type user: User
        :param chat: The chat session instance associated with this request.
        :type chat: Chat
        :param data: The request payload, typically containing a session key and a list of message dictionaries.
        :type data: dict

            Example::

                {
                    'session_key': '6f3bdd1981e0cac2de5fdc7afc2fb4e565826473a124153220e9f6bf49bca67b',
                    'messages': [
                        {'role': 'system', 'content': "You are a helpful assistant."},
                        {'role': 'assistant', 'content': "Welcome to Smarter! ..."},
                        {'role': 'smarter', 'content': "Tool call: smarter_plugin_0002({\"inquiry_type\":\"about\"})"},
                        {'role': 'user', 'content': 'Hello, World!'}
                    ]
                }

        :param plugins: A list of plugin instances to be considered for selection and presentation to the LLM.
        :type plugins: Optional[list[PluginBase]]
        :param functions: A list of predefined function definitions for tool calls.
        :type functions: Optional[list[str]]

        :returns: An HTTP response dictionary (or list) containing the LLM's output, tool call results, and metadata.
        :rtype: dict or list

        :raises SmarterValueError: If required parameters are missing or invalid.
        :raises SmarterConfigurationError: If there are configuration issues with the provider or plugins.
        :raises SmarterIlligalInvocationError: If the method is invoked in an invalid state.

        .. note::

            This method manages both the initial and any required follow-up LLM requests (e.g., for tool calls).
            It also handles plugin selection logic and ensures that all required signals and billing events are triggered.

        .. seealso::

            :class:`InternalKeys`
            :class:`OpenAIMessageKeys`
            :class:`PluginBase`
            :class:`ChatCompletion`
            :class:`ChatCompletionMessageToolCall`

        Example usage::

            response = provider.handler(
                chat=chat_instance,
                data=request_data,
                plugins=[plugin1, plugin2],
                functions=[function_definition_1, function_definition_2],
                user=current_user
            )
        """
        plugins_list = [plugin.name for plugin in plugins] if plugins else []
        logger.debug(
            "%s.handler() called with user=%s, chat=%s, plugins=%s, functions=%s",
            self.formatted_class_name,
            user,
            chat,
            plugins_list,
            functions,
        )
        self._chat = chat
        self.user = user
        if chat:
            self.user_profile = chat.user_profile
        self.data = data
        self.plugins = plugins
        self.functions = functions

        chat_started.send(sender=self.handler, chat=self.chat, data=self.data)
        self.iteration = 1
        openai.api_key = self.api_key
        openai.base_url = self.base_url

        try:
            self.validate()
            self.model = self.chat.chatbot.default_model or self.default_model
            self.temperature = self.chat.chatbot.default_temperature or self.default_temperature
            self.max_completion_tokens = self.chat.chatbot.default_max_tokens or self.default_max_tokens
            if not self.data:
                raise SmarterValueError(f"{self.formatted_class_name}: data is required")
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
                self.messages = self.get_message_thread(data=self.data)

            # add plugins to the prompt if any are selected
            if self.plugins:
                for plugin in self.plugins:
                    if plugin.selected(user=self.user, input_text=self.input_text, messages=self.messages):
                        self.handle_plugin_selected(plugin=plugin)

            # add all functions that are included in the chatbot definition
            # LAWRENCE
            if self.functions:
                for function in self.functions:
                    self.handle_function_provided(function)

            self.prep_first_request()
            completions_kwargs = {
                InternalKeys.MODEL_KEY: self.model,
                InternalKeys.MESSAGES_KEY: self.openai_messages,
                InternalKeys.TEMPERATURE_KEY: self.temperature,
                InternalKeys.MAX_COMPLETION_TOKENS_KEY: self.max_completion_tokens,
            }
            if self.tools:
                # new rule: tool_choice should only be provided if there are
                # actual tools included in the request, otherwise OpenAI's
                # API returns a 400 error: 'Invalid value 'tool_choice'
                # is only allowed when 'tools' are specified.'
                completions_kwargs[InternalKeys.TOOLS_KEY] = self.tools
                completions_kwargs[InternalKeys.TOOL_CHOICE] = OPENAI_TOOL_CHOICE
            completions_kwargs = self.prune_empty_values(completions_kwargs)

            logger.debug(
                "%s %s - openai.chat.completions.create() completions_kwargs: %s",
                self.formatted_class_name,
                formatted_text("handler()"),
                completions_kwargs,
            )

            self.first_response = openai.chat.completions.create(**completions_kwargs)  # type: ignore[call-arg]
            if not isinstance(self.first_response, ChatCompletion):
                raise SmarterValueError(
                    f"{self.formatted_class_name}: first_response must be a ChatCompletion, got {type(self.first_response)}"
                )
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
                self.append_openai_response(self.second_response)
                self.handle_response()

        # handle anything that went wrong
        # pylint: disable=broad-exception-caught
        except Exception as e:
            stack_trace = traceback.format_exc()
            chat_response_failure.send(
                sender=self.handler,
                iteration=self.iteration,
                chat=self.chat,
                request_meta_data=self.request_meta_data,
                exception=e,
                first_iteration=self.first_iteration,
                second_iteration=self.second_iteration,
                messages=self.messages,
                stack_trace=stack_trace,
            )
            status_code, _message = EXCEPTION_MAP.get(
                type(e), (HTTPStatus.INTERNAL_SERVER_ERROR.value, "Internal server error")
            )
            retval = http_response_factory(
                status_code=status_code,
                body=exception_response_factory(exception=e, request_meta_data=self.request_meta_data),
            )
            if not isinstance(retval, dict) and not isinstance(retval, list):
                raise SmarterValueError(
                    f"{self.formatted_class_name}: retval must be an HttpResponse, got {type(retval)}"
                ) from e
            return retval

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
