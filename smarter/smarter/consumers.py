"""
WebSocket URL routing for the smarter application.

- ``ws/terminal/``: the web console terminal, a bash shell in the server's container, for
  superusers. See :mod:`smarter.apps.dashboard.views.terminal_emulator.api.consumers`.
"""

from smarter.apps.dashboard.views.terminal_emulator.api import (
    consumers as terminal_consumers,
)

urlpatterns = [
    *terminal_consumers.urlpatterns,
]

__all__ = ["urlpatterns"]
