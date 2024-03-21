# -*- coding: utf-8 -*-
# pylint: disable=W0613,C0115
"""Signals for chat app."""
from django.dispatch import Signal


# chat signals
chat_invoked = Signal()
chat_response_success = Signal()
chat_response_failure = Signal()

# chat completion plugin selection
chat_completion_plugin_selected = Signal()
chat_completion_plugin_usage_history_created = Signal()

# chat completion signals
chat_completion_called = Signal()
chat_completion_history_created = Signal()

# chat completion tools signals
chat_completion_tools_call = Signal()
chat_completion_tool_call_created = Signal()
chat_completion_tool_call_received = Signal()
chat_completion_tool_call_history_created = Signal()
