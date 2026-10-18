"""
Django signal receivers for the llmtool app.

Each module holds the receivers of one kind of work, alongside its signals in
:mod:`smarter.apps.llmtool.signals`. Importing this package, as
:meth:`smarter.apps.llmtool.apps.PluginConfig.ready` does, connects them all.

- :mod:`.plugin`: the lifecycle of every plugin.
- :mod:`.models`: the llmtool Django models' post_save and pre_delete signals.
- :mod:`.websearch`: WebsearchPlugin searches and page reads.
- :mod:`.extension`: Smarter Extensions.
- :mod:`.sql`, :mod:`.api`, :mod:`.image_search` and :mod:`.skill`: the request lifecycle
  of each plugin kind's tool calls.
"""

from . import (  # noqa: F401
    api,
    extension,
    image_search,
    models,
    plugin,
    skill,
    sql,
    websearch,
)
from .utils import response_characters

__all__ = ["api", "extension", "image_search", "models", "plugin", "response_characters", "skill", "sql", "websearch"]
