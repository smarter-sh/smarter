"""
Base class for chat providers.
"""

import logging
from http import HTTPStatus
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel

from smarter.apps.account.tasks import (
    create_plugin_charge,
    create_prompt_completion_charge,
)
from smarter.apps.chat.functions.function_weather import (
    get_current_weather,
    weather_tool_factory,
)
from smarter.apps.chat.models import Chat
from smarter.apps.chat.signals import chat_provider_initialized
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.common.exceptions import (
    SmarterConfigurationError,
    SmarterIlligalInvocationError,
    SmarterValueError,
)
from smarter.common.helpers.console_helpers import formatted_text

from .openai.const import OpenAIMessageKeys


logger = logging.getLogger(__name__)

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


class HandlerInputBase(BaseModel):
    """
    Input protocol for chat provider handlers. Using OpenAI defaults.
    Providers should subclass this and override the defaults.
    """

    chat: Chat
    data: dict
    plugins: Optional[List[PluginStatic]] = None
    user: Optional[Any] = None

    # OpenAI defaults. Subclassed providers should override these.
    default_model: str
    default_system_role: str
    default_temperature: float
    default_max_tokens: int

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class ChatProviderBase:
    """
    Base class for chat providers.
    """

    _messages: List[Dict[str, str]] = []

    # built-in tools that we make available to all providers
    weather_tool = weather_tool_factory()
    tools = [weather_tool]
    available_functions = {
        "get_current_weather": get_current_weather,
    }

    def __init__(
        self, name: str, default_model: str, exception_map: dict = None, base_url: str = None, api_key: str = None
    ):
        self._name = name
        self.base_url = base_url
        self.api_key = api_key
        self._default_model = default_model
        self._exception_map = exception_map or BASE_EXCEPTION_MAP
        self.init()
        chat_provider_initialized.send(sender=self)

    def init(self):
        self._messages = []

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

    def handle_first_prompt(
        self,
        model: str,
        tools: List[dict],
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ):
        message = f"Prompt configuration: llm={self.name}, model={model}, temperature={temperature}, max_tokens={max_tokens}, tool_choice={tool_choice}."
        self.append_message(OpenAIMessageKeys.SMARTER_MESSAGE_KEY, message)

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

    def handle_prompt_completion_response(
        self,
        user_id: int,
        model: str,
        completion_tokens: int,
        prompt_tokens: int,
        total_tokens: int,
        system_fingerprint: str,
        response_message_role: str,
        response_message_content: str,
    ) -> None:
        """
        handle internal billing, and append messages to the response for prompt completion and the billing summary
        """
        logger.info("%s %s", self.formatted_class_name, formatted_text("handle_prompt_completion_response()"))
        create_prompt_completion_charge.delay(
            user_id, model, completion_tokens, prompt_tokens, total_tokens, system_fingerprint
        )
        self.append_message(
            role=OpenAIMessageKeys.SMARTER_MESSAGE_KEY,
            message=f"{self.name} prompt charges: {prompt_tokens} prompt tokens, {completion_tokens} completion tokens = {total_tokens} total tokens charged.",
        )
        self.append_message(role=response_message_role, message=response_message_content)

    def handle_prompt_completion_plugin(
        self,
        user_id: int,
        model: str,
        completion_tokens: int,
        prompt_tokens: int,
        total_tokens: int,
        system_fingerprint: str,
    ) -> None:
        logger.info("%s %s", self.formatted_class_name, formatted_text("handle_prompt_completion_plugin()"))
        create_plugin_charge.delay(
            user_id=user_id,
            model=model,
            completion_tokens=completion_tokens,
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens,
            fingerprint=system_fingerprint,
        )

    @property
    def formatted_class_name(self):
        return formatted_text(self.__class__.__name__)

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def exception_map(self) -> Dict[Type[Exception], Tuple[HTTPStatus, str]]:
        return self._exception_map

    @property
    def valid_models(self) -> list[str]:
        pass

    def handler(self, handler_inputs: Type[HandlerInputBase]) -> Callable:
        """
        Handle the chat request.

        :param handler_input: The input protocol for chat provider handlers.
            chat = handler_input.chat
            data = handler_input.data
            plugins = handler_input.plugins
            user = handler_input.user
            default_model = handler_input.default_model
            default_system_role = handler_input.default_system_role
            default_temperature = handler_input.default_temperature
            default_max_tokens = handler_input.default_max_tokens
        """

    def _validate_default_model(self, model: str) -> None:
        if model not in self.valid_models:
            raise ValueError(
                f"Internal error. Invalid default model: {model} not found in list of valid {self.name} models {self.valid_models}."
            )
