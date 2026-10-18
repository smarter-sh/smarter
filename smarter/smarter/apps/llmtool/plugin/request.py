"""
The request lifecycle signals of a plugin's tool call.

A tool call to a SqlPlugin, ApiPlugin, ImageSearchPlugin or SkillPlugin sends one family of
:mod:`smarter.apps.llmtool.signals`, in this order:

1. ``<family>_request_started``, when the tool call begins.
2. ``<family>_authenticated`` or ``<family>_authentication_failed``, when the plugin's remote
   service accepts or rejects its credentials. Families without credentials have neither, and
   a response served from the cache sends neither, since nothing was authenticated.
3. ``<family>_responded``, with the response, or ``<family>_failed``, with the error.
4. ``<family>_request_completed``, always, with whether the request succeeded and how long it took.

:class:`PluginRequest` sends them, so that each plugin sends them the same way.

**Example:**

.. code-block:: python

    with PluginRequest(SQL_PLUGIN_REQUEST_SIGNALS, sender=self.__class__, plugin=self, function_args=function_args) as request:
        ...
        request.authenticated(connection=sql_connection.name)
        ...
        request.responded(response=retval, cached=False)
"""

import time
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Type, Union

from django.dispatch import Signal

from smarter.apps.llmtool.signals import (
    api_plugin_authenticated,
    api_plugin_authentication_failed,
    api_plugin_failed,
    api_plugin_request_completed,
    api_plugin_request_started,
    api_plugin_responded,
    image_search_plugin_authenticated,
    image_search_plugin_authentication_failed,
    image_search_plugin_failed,
    image_search_plugin_request_completed,
    image_search_plugin_request_started,
    image_search_plugin_responded,
    skill_plugin_failed,
    skill_plugin_request_completed,
    skill_plugin_request_started,
    skill_plugin_responded,
    sql_plugin_authenticated,
    sql_plugin_authentication_failed,
    sql_plugin_failed,
    sql_plugin_request_completed,
    sql_plugin_request_started,
    sql_plugin_responded,
)
from smarter.lib.typing import SmarterDictType

if TYPE_CHECKING:
    from .base import PluginBase


@dataclass(frozen=True)
class PluginRequestSignals:
    """
    One plugin family's request lifecycle signals.

    :ivar started: Sent when a tool call begins.
    :ivar responded: Sent with the response.
    :ivar failed: Sent with the error, if the tool call fails.
    :ivar completed: Sent when the tool call ends, successfully or not.
    :ivar authenticated: Sent when the remote service accepts the plugin's credentials. None if the family has no credentials.
    :ivar authentication_failed: Sent when the remote service rejects them. None if the family has no credentials.
    """

    started: Signal
    responded: Signal
    failed: Signal
    completed: Signal
    authenticated: Optional[Signal] = None
    authentication_failed: Optional[Signal] = None


SQL_PLUGIN_REQUEST_SIGNALS = PluginRequestSignals(
    started=sql_plugin_request_started,
    responded=sql_plugin_responded,
    failed=sql_plugin_failed,
    completed=sql_plugin_request_completed,
    authenticated=sql_plugin_authenticated,
    authentication_failed=sql_plugin_authentication_failed,
)
"""The SqlPlugin request lifecycle signals."""

API_PLUGIN_REQUEST_SIGNALS = PluginRequestSignals(
    started=api_plugin_request_started,
    responded=api_plugin_responded,
    failed=api_plugin_failed,
    completed=api_plugin_request_completed,
    authenticated=api_plugin_authenticated,
    authentication_failed=api_plugin_authentication_failed,
)
"""The ApiPlugin request lifecycle signals."""

IMAGE_SEARCH_PLUGIN_REQUEST_SIGNALS = PluginRequestSignals(
    started=image_search_plugin_request_started,
    responded=image_search_plugin_responded,
    failed=image_search_plugin_failed,
    completed=image_search_plugin_request_completed,
    authenticated=image_search_plugin_authenticated,
    authentication_failed=image_search_plugin_authentication_failed,
)
"""The ImageSearchPlugin request lifecycle signals."""

SKILL_PLUGIN_REQUEST_SIGNALS = PluginRequestSignals(
    started=skill_plugin_request_started,
    responded=skill_plugin_responded,
    failed=skill_plugin_failed,
    completed=skill_plugin_request_completed,
)
"""The SkillPlugin request lifecycle signals.

A SkillPlugin's tool call reads its stored skill, so it has no credentials.
"""


class PluginRequest:
    """
    Send a plugin family's request lifecycle signals for one tool call.

    Entering the context sends ``started``. Leaving it sends ``failed`` if an exception
    escapes and :meth:`failed` was not already called, and then ``completed``. Exceptions are
    never suppressed.

    :param signals: The plugin family's signals.
    :param sender: The signals' sender, usually the plugin's class.
    :param plugin: The plugin, which every signal sends.
    :param function_args: The tool call's arguments, which ``started`` sends.
    """

    def __init__(
        self,
        signals: PluginRequestSignals,
        sender: type,
        plugin: "PluginBase",
        function_args: Union[SmarterDictType, list, str, None] = None,
    ):
        self.signals = signals
        self.sender = sender
        self.plugin = plugin
        self.function_args = function_args
        self.has_failed = False
        self.cached = False
        """Set by the plugin, when its response was served from the cache."""
        self.start_time: Optional[float] = None

    def __enter__(self) -> "PluginRequest":
        self.start_time = time.monotonic()
        self.signals.started.send(sender=self.sender, plugin=self.plugin, function_args=self.function_args)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> bool:
        if exc_value is not None and not self.has_failed:
            self.failed(error=str(exc_value))
        self.signals.completed.send(
            sender=self.sender,
            plugin=self.plugin,
            success=not self.has_failed,
            duration=self.duration,
        )
        return False

    @property
    def duration(self) -> float:
        """The seconds since the request started."""
        return time.monotonic() - self.start_time if self.start_time is not None else 0.0

    def authenticated(self, **kwargs) -> None:
        """Send ``authenticated``, with the plugin and ``kwargs``, if the family has credentials."""
        if self.signals.authenticated:
            self.signals.authenticated.send(sender=self.sender, plugin=self.plugin, **kwargs)

    def authentication_failed(self, error: str, **kwargs) -> None:
        """
        Send ``authentication_failed``, with the plugin, the error and ``kwargs``, if the family has credentials.

        :param error: What went wrong. It must not contain the credentials.
        """
        if self.signals.authentication_failed:
            self.signals.authentication_failed.send(sender=self.sender, plugin=self.plugin, error=error, **kwargs)

    def responded(self, response: Union[SmarterDictType, list, str, None], cached: bool = False, **kwargs) -> None:
        """
        Send ``responded``.

        :param response: The response that the tool call returns to the LLM.
        :param cached: True if the response was served from the cache.
        """
        self.signals.responded.send(sender=self.sender, plugin=self.plugin, response=response, cached=cached, **kwargs)

    def failed(self, error: str, **kwargs) -> None:
        """
        Send ``failed``, and mark the request as failed.

        :param error: What went wrong. It must not contain secrets.
        """
        self.has_failed = True
        self.signals.failed.send(sender=self.sender, plugin=self.plugin, error=error, **kwargs)


__all__ = [
    "API_PLUGIN_REQUEST_SIGNALS",
    "IMAGE_SEARCH_PLUGIN_REQUEST_SIGNALS",
    "SKILL_PLUGIN_REQUEST_SIGNALS",
    "SQL_PLUGIN_REQUEST_SIGNALS",
    "PluginRequest",
    "PluginRequestSignals",
]
