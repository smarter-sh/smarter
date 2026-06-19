# pylint: disable=W0613,C0115
"""Signals for prompt app."""

from django.dispatch import Signal

# prompt signals
prompt_started = Signal()
prompt_finished = Signal()
chat_response_failure = Signal()


# prompt completion signals
chat_completion_request = Signal()
chat_completion_response = Signal()

# prompt completion tools signals
chat_completion_tool_called = Signal()
chat_completion_plugin_called = Signal()

llm_provider_initialized = Signal()
prompt_handler_console_output = Signal()

llm_tool_presented = Signal()
llm_tool_requested = Signal()
llm_tool_responded = Signal()

prompt_session_invoked = Signal()
prompt_config_invoked = Signal()
