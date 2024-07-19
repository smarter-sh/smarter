# pylint: disable=W0613,C0115
"""Signals for chat app."""
from django.dispatch import Signal


# chat signals
chat_invoked = Signal()
chat_response_success = Signal()
chat_response_failure = Signal()

# chat completion plugin selection
chat_completion_plugin_selected = Signal()

# chat completion signals
chat_completion_called = Signal()

# chat completion tools signals
chat_completion_tool_call_created = Signal()

# chat completion invalid tool calls signal
chat_completion_invalid_tool_call = Signal()
