"""
Smarter Extensions: installable Python packages that add LLM tools to the platform.

An Extension is code, where a Plugin (:mod:`smarter.apps.llmtool.plugin`) is configuration:
a Plugin is a SAM resource that configures one of Smarter's predefined tool patterns
(Sql, Api, Skill, Websearch, ...), while an Extension is a Python package, with its own
tools, settings, documentation, assets and lifecycle, that a platform administrator
installs at run time from the Django admin console or the extension registry.

The modules of this package:

- :mod:`.manifest`: the extension's ``pyproject.toml``.
- :mod:`.archive`: the extension's zip archive.
- :mod:`.protocol`: :class:`SmarterExtensionTool`, the base class of an extension's tools.
- :mod:`.lifecycle`: :class:`SmarterExtensionLifecycle`, its install, upgrade and uninstall hooks.
- :mod:`.settings`: its settings, as its code sees them.
- :mod:`.loader`: importing its code into each process.
- :mod:`.installer`: :class:`ExtensionInstaller`, every administrator action.
- :mod:`.toolkit`: :class:`ExtensionToolkit`, its tools in a prompt.
- :mod:`.registry`: the extension registry, for discovery and updates.

An extension's code imports what it needs from this package:

.. code-block:: python

    from smarter.apps.llmtool.extension import (
        ExtensionContext,
        ExtensionToolError,
        LifecycleContext,
        SmarterExtensionLifecycle,
        SmarterExtensionTool,
    )
"""

from .lifecycle import LifecycleContext, SmarterExtensionLifecycle
from .protocol import ExtensionContext, ExtensionToolError, SmarterExtensionTool

__all__ = [
    "ExtensionContext",
    "ExtensionToolError",
    "LifecycleContext",
    "SmarterExtensionLifecycle",
    "SmarterExtensionTool",
]
