"""
Signals for the llmtool app.

Each module holds the signals of one kind of work, and this package re-exports them all, so
that ``from smarter.apps.llmtool.signals import plugin_called`` works for every signal.

- :mod:`.plugin`: the lifecycle of every plugin: create, clone, update, delete, select and call.
- :mod:`.websearch`: WebsearchPlugin searches and page reads.
- :mod:`.extension`: Smarter Extensions: installation, and calls to their tools.
- :mod:`.sql`, :mod:`.api`, :mod:`.image_search` and :mod:`.skill`: the request lifecycle
  signals of each plugin kind's tool calls. See :mod:`smarter.apps.llmtool.plugin.request`.
"""

from .api import (
    api_plugin_authenticated,
    api_plugin_authentication_failed,
    api_plugin_failed,
    api_plugin_request_completed,
    api_plugin_request_started,
    api_plugin_responded,
)
from .extension import (
    extension_disabled,
    extension_enabled,
    extension_installed,
    extension_tool_called,
    extension_tool_completed,
    extension_tool_failed,
    extension_tool_responded,
    extension_uninstalled,
    extension_upgraded,
)
from .image_search import (
    image_search_plugin_authenticated,
    image_search_plugin_authentication_failed,
    image_search_plugin_failed,
    image_search_plugin_request_completed,
    image_search_plugin_request_started,
    image_search_plugin_responded,
)
from .plugin import (
    broker_ready,
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_deleting,
    plugin_ready,
    plugin_responded,
    plugin_selected,
    plugin_updated,
    search_term_matched,
)
from .skill import (
    skill_plugin_failed,
    skill_plugin_request_completed,
    skill_plugin_request_started,
    skill_plugin_responded,
    skill_plugin_retrieval_failed,
    skill_plugin_retrieval_started,
    skill_plugin_retrieved,
)
from .sql import (
    sql_plugin_authenticated,
    sql_plugin_authentication_failed,
    sql_plugin_failed,
    sql_plugin_request_completed,
    sql_plugin_request_started,
    sql_plugin_responded,
)
from .websearch import (
    websearch_failed,
    websearch_fetched,
    websearch_searched,
)

__all__ = [
    "api_plugin_authenticated",
    "api_plugin_authentication_failed",
    "api_plugin_failed",
    "api_plugin_request_completed",
    "api_plugin_request_started",
    "api_plugin_responded",
    "broker_ready",
    "extension_disabled",
    "extension_enabled",
    "extension_installed",
    "extension_tool_called",
    "extension_tool_completed",
    "extension_tool_failed",
    "extension_tool_responded",
    "extension_uninstalled",
    "extension_upgraded",
    "image_search_plugin_authenticated",
    "image_search_plugin_authentication_failed",
    "image_search_plugin_failed",
    "image_search_plugin_request_completed",
    "image_search_plugin_request_started",
    "image_search_plugin_responded",
    "plugin_called",
    "plugin_cloned",
    "plugin_created",
    "plugin_deleted",
    "plugin_deleting",
    "plugin_ready",
    "plugin_responded",
    "plugin_selected",
    "plugin_updated",
    "search_term_matched",
    "skill_plugin_failed",
    "skill_plugin_request_completed",
    "skill_plugin_request_started",
    "skill_plugin_responded",
    "skill_plugin_retrieval_failed",
    "skill_plugin_retrieval_started",
    "skill_plugin_retrieved",
    "sql_plugin_authenticated",
    "sql_plugin_authentication_failed",
    "sql_plugin_failed",
    "sql_plugin_request_completed",
    "sql_plugin_request_started",
    "sql_plugin_responded",
    "websearch_failed",
    "websearch_fetched",
    "websearch_searched",
]
