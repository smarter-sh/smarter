"""
Base class for chat providers.
"""

import logging
from functools import cached_property
from typing import Any, Dict, List, Optional, Union

from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCallUnion,
)

from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.functions.calculator import (
    calculator,
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
from smarter.apps.prompt.providers.const import OpenAIMessageKeys
from smarter.apps.prompt.providers.utils import (
    ensure_system_role_present,
    get_request_body,
    parse_request,
)
from smarter.apps.prompt.signals import (
    chat_provider_initialized,
)
from smarter.common.exceptions import (
    SmarterValueError,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.helpers.llm import get_date_time_string
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from . import ChatDbMixin
from .internal_keys import _InternalKeys


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SmarterChatProviderBase(ChatDbMixin):
    """
    Base class for all Smarter chat providers.

    This class defines the core interface and shared logic for chat providers
    that interact with ChatBots via the Smarter API, including both the
    Reactapp and deployed ChatBots accessible through named URLs. It is
    designed to be subclassed by specific provider implementations.

    The API is largely a superset of the OpenAI chat completion API, with
    additional properties and methods for configuring the Reactapp and for
    managing additional message content types that are proprietary to Smarter.

    **Key Features:**

        - Provides a unified interface for chat providers, supporting both OpenAI-compatible and proprietary Smarter features.
        - Handles message thread management, including system prompts, user/assistant messages, and plugin/tool messages.
        - Supports built-in tools (e.g., weather, date calculator) and plugin integration.
        - Manages provider configuration, validation, and readiness checks.
        - Tracks token usage and charge insertion for billing/auditing.

    **Usage:**

        Subclass this base class to implement a new chat provider. Override or extend methods as needed for provider-specific logic.

    **Example:**
        .. code-block:: python

            class MyProvider(SmarterChatProviderBase):
                def my_custom_method(self):
                    # Custom logic here
                    pass

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
    plugins: Optional[List[PluginBase]]
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
        """
        Initialize the SmarterChatProviderBase with the given parameters.

        :param provider: The name of the chat provider (e.g., "openai", "google").
        :type provider: str
        :param base_url: The base URL for the chat provider's API.
        :type base_url: str
        :param api_key: The API key for authenticating with the chat provider.
        :type api_key: str
        :param default_model: The default model to use for chat completions.
        :type default_model: str
        :param default_system_role: The default system role to use in the message thread.
        :type default_system_role: str
        :param default_temperature: The default temperature to use for chat completions.
        :type default_temperature: float
        :param default_max_tokens: The default maximum number of tokens for chat completions.
        :type default_max_tokens: int
        :param valid_chat_completion_models: A list of valid chat completion models for the provider.
        :type valid_chat_completion_models: list[str]
        :param add_built_in_tools: Whether to add built-in tools (weather and date calculator) to the provider.
        :type add_built_in_tools: bool




        """
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
            _InternalKeys.REQUEST_KEY: None,
            _InternalKeys.RESPONSE_KEY: None,
        }
        self.first_response = None
        self.second_response = None
        self.second_iteration = {
            _InternalKeys.REQUEST_KEY: {_InternalKeys.MESSAGES_KEY: []},
            _InternalKeys.RESPONSE_KEY: {},
            _InternalKeys.MESSAGES_KEY: [],
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
            self.account = self.chat.user_profile.account

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
        return formatted_text(f"{__name__}.{SmarterChatProviderBase.__name__}[{id(self)}]")

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
            new_message[_InternalKeys.SMARTER_IS_NEW] = is_new
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
        new_message[_InternalKeys.SMARTER_IS_NEW] = True
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
        content = f"{self.provider} called this tool: {tool_call.function.name}({tool_call.function.arguments})"  # type: ignore
        content = content + f"\n\nTool call:\n--------------------\n{json.dumps(tool_call_to_json, indent=4)}"
        self.append_message(role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY, content=content)

    def append_error_response(self, error_message: str) -> None:
        """
        Append a message indicating that an error occurred.

        :param error_message: The error message to append.
        :type error_message: str
        :returns: None
        :rtype: None
        """
        content = f"LLM responded with the following error: {error_message}"
        self.append_message(role=OpenAIMessageKeys.SMARTER_ERROR_KEY, content=content)

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
            reference=self.reference or "SmarterChatProviderBase._insert_charge_by_type()",
        )


__all__ = ["SmarterChatProviderBase"]
