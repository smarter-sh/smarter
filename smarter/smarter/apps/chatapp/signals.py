"""Signals for chatapp app."""

from django.dispatch import Signal


chat_session_invoked = Signal()
chat_config_invoked = Signal()
