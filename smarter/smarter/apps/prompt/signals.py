# pylint: disable=W0613,C0115
"""Signals for prompt app."""

from django.dispatch import Signal

# prompt signals
prompt_started = Signal()
prompt_finished = Signal()

# chat completion (aka text completion) signals
chat_request = Signal()
chat_response = Signal()
chat_tool_called = Signal()
chat_plugin_called = Signal()
chat_response_failure = Signal()

llm_provider_initialized = Signal()
llm_tool_presented = Signal()
llm_tool_requested = Signal()
llm_tool_responded = Signal()

prompt_handler_console_output = Signal()
prompt_session_invoked = Signal()
prompt_config_invoked = Signal()
