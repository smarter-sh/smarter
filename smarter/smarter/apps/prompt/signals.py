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

llm_tool_presented = Signal()
llm_tool_requested = Signal()
llm_tool_responded = Signal()

chat_session_invoked = Signal()
chat_config_invoked = Signal()
