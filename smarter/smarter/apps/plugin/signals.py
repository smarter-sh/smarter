# -*- coding: utf-8 -*-
"""Signals for plugin app."""
from django.dispatch import Signal


plugin_created = Signal()
plugin_cloned = Signal()
plugin_updated = Signal()
plugin_deleted = Signal()
plugin_called = Signal()

plugin_ready = Signal()
plugin_selected_called = Signal()
plugin_selected = Signal()
plugin_selector_history_created = Signal()
