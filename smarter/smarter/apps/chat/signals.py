# -*- coding: utf-8 -*-
# pylint: disable=W0613,C0115
"""Signals for account app."""
from django.dispatch import Signal


# plugin signals
chat_completion_plugin_selected = Signal()
chat_completion_plugin_selection_history_created = Signal()

# chat signals
chat_invoked = Signal()
chat_completion_called = Signal()
chat_completion_returned = Signal()
chat_completion_failed = Signal()

# chat history signals
chat_completion_history_created = Signal()
chat_completion_tools_call = Signal()
chat_completion_tool_call_created = Signal()
chat_completion_tool_call_received = Signal()
chat_completion_tool_call_history_created = Signal()
