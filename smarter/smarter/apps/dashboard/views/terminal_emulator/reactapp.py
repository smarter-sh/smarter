"""
The web console's Terminal page: a bash shell inside the server's container, for superusers.

The page is the single-page console's (ADR-035): it renders ``@smarter/terminal-emulator``, which draws a window
styled after macOS Terminal.app with xterm.js. The terminal POSTs to the ticket api for a single use ticket, then
opens the terminal's WebSocket with it, which runs a bash shell in the server process that accepts it. See
:mod:`.api.tickets` and :mod:`.api.consumers`.

Classes:
    TerminalEmulatorView: The Terminal page, which Django keeps at the path it served the page at.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.terminal_emulator.enabled import require_terminal
        from smarter.apps.dashboard.views.terminal_emulator.reactapp import TerminalEmulatorView

        urlpatterns = [
            path("terminal/", require_terminal(TerminalEmulatorView.as_view()), name="terminal_emulator_view"),
        ]
"""

from smarter.apps.dashboard.views.console_app import ConsoleAppView


class TerminalEmulatorView(ConsoleAppView):
    """
    The Terminal page, ``/dashboard/terminal/``: the single-page console's.

    The url patterns wrap it in :func:`.enabled.require_terminal`, so that the page is a 404 while the terminal is
    disabled, and for every user but a superuser, as the ticket api is. The console's session says the same, so that
    a user who reaches the page within the console sees its Page not found.
    """
