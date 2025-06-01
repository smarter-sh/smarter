"""Signals for plugin app."""

from django.dispatch import Signal


plugin_created = Signal()
plugin_cloned = Signal()
plugin_updated = Signal()
plugin_deleted = Signal()
plugin_called = Signal()

plugin_ready = Signal()
plugin_selected = Signal()

plugin_sql_connection_attempted = Signal()
plugin_sql_connection_success = Signal()
plugin_sql_connection_failed = Signal()
plugin_sql_connection_query_attempted = Signal()
plugin_sql_connection_query_success = Signal()
plugin_sql_connection_query_failed = Signal()

plugin_api_connection_attempted = Signal()
plugin_api_connection_success = Signal()
plugin_api_connection_failed = Signal()
plugin_api_connection_query_attempted = Signal()
plugin_api_connection_query_success = Signal()
plugin_api_connection_query_failed = Signal()
