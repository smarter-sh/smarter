# pylint: disable=W0613,C0115
"""Signals for chat app."""
from django.dispatch import Signal


# chat signals
chat_started = Signal()
chat_finished = Signal()
chat_response_failure = Signal()


# chat completion signals
chat_completion_request = Signal()
chat_completion_response = Signal()

# chat completion tools signals
chat_completion_tool_called = Signal()
chat_completion_plugin_called = Signal()

chat_provider_initialized = Signal()
chat_handler_console_output = Signal()

get_current_weather_request = Signal()
get_current_weather_response = Signal()
