"""Signals of Smarter Extensions: installation, and calls to their tools."""

from django.dispatch import Signal

extension_installed = Signal()
"""
Signal sent after an extension is installed for the first time.

Arguments:
    extension: The Extension.
    version: The ExtensionVersion that was installed.

Example::

    extension_installed.send(sender=self.__class__, extension=extension, version=version)
"""

extension_upgraded = Signal()
"""
Signal sent after an installed extension's version changes, by an update or a rollback.

Arguments:
    extension: The Extension.
    version: The ExtensionVersion that now runs.
    previous_version: The version string that it replaced.

Example::

    extension_upgraded.send(sender=self.__class__, extension=extension, version=version, previous_version="1.0.0")
"""

extension_uninstalled = Signal()
"""
Signal sent after an extension is uninstalled.

Arguments:
    slug: The slug of the extension that was uninstalled.

Example::

    extension_uninstalled.send(sender=self.__class__, slug="weather")
"""

extension_enabled = Signal()
"""
Signal sent after an extension is enabled.

Arguments:
    extension: The Extension.

Example::

    extension_enabled.send(sender=self.__class__, extension=extension)
"""

extension_disabled = Signal()
"""
Signal sent after an extension is disabled.

Arguments:
    extension: The Extension.
    reason: Why it was disabled, e.g. a lifecycle hook failed, or an administrator disabled it.

Example::

    extension_disabled.send(sender=self.__class__, extension=extension, reason="disabled by admin")
"""

extension_tool_called = Signal()
"""
Signal sent when an LLM calls one of an extension's tools.

Arguments:
    slug: The extension's slug.
    version: The extension's version.
    tool_name: The tool's name.
    arguments: The arguments the LLM sent.

Example::

    extension_tool_called.send(sender=self.__class__, slug="weather", version="1.0.0", tool_name="get_weather", arguments={})
"""

extension_tool_responded = Signal()
"""
Signal sent when one of an extension's tools returns a result.

Arguments:
    slug: The extension's slug.
    version: The extension's version.
    tool_name: The tool's name.
    characters: The length of the result, as JSON.

Example::

    extension_tool_responded.send(sender=self.__class__, slug="weather", version="1.0.0", tool_name="get_weather", characters=1024)
"""

extension_tool_failed = Signal()
"""
Signal sent when one of an extension's tools fails: its arguments are invalid, it raises, or it times out.

Arguments:
    slug: The extension's slug.
    version: The extension's version.
    tool_name: The tool's name.
    error: What went wrong.

Example::

    extension_tool_failed.send(sender=self.__class__, slug="weather", version="1.0.0", tool_name="get_weather", error="timed out")
"""

extension_tool_completed = Signal()
"""
Signal sent when a call to one of an extension's tools ends, successfully or not.

It is always the last signal of the call.

Arguments:
    slug: The extension's slug.
    version: The extension's version.
    tool_name: The tool's name.
    success: False if extension_tool_failed was sent.
    duration: The seconds that the call took.

Example::

    extension_tool_completed.send(sender=self.__class__, slug="weather", version="1.0.0", tool_name="get_weather", success=True, duration=0.8)
"""
