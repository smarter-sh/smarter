"""
Base class for chat providers.
"""

import logging
from abc import ABC, abstractmethod
from http import HTTPStatus
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel

from smarter.apps.chat.functions.function_weather import (
    get_current_weather,
    weather_tool_factory,
)
from smarter.apps.chat.models import Chat
from smarter.apps.chat.signals import chat_provider_initialized
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.common.classes import Singleton
from smarter.common.exceptions import (
    SmarterConfigurationError,
    SmarterIlligalInvocationError,
    SmarterValueError,
)
from smarter.common.helpers.console_helpers import formatted_text


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


class HandlerInputBase(BaseModel, ABC):
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


class CombinedMeta(type(ABC), Singleton):
    """
    Metaclass for combining ABC and Singleton.
    """


class ChatProviderBase(ABC, metaclass=CombinedMeta):
    """
    Base class for chat providers.
    """

    @abstractmethod
    def __init__(
        self, name: str, default_model: str, exception_map: dict = None, base_url: str = None, api_key: str = None
    ):
        self._name = name
        self.base_url = base_url
        self.api_key = api_key
        self._default_model = default_model
        self._exception_map = exception_map or BASE_EXCEPTION_MAP
        chat_provider_initialized.send(sender=self)

    # built-in tools that we make available to all providers
    weather_tool = weather_tool_factory()
    tools = [weather_tool]
    available_functions = {
        "get_current_weather": get_current_weather,
    }

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
    @abstractmethod
    def valid_models(self) -> list[str]:
        pass

    @abstractmethod
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
