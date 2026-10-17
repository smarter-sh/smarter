"""Constants for the dashboard's server logs api and the web console terminal."""

namespace = "api"

TERMINAL_WEBSOCKET_PATH = "ws/terminal/"
"""The path of the terminal's WebSocket, relative to the site's root.

See :mod:`smarter.consumers`.
"""

TERMINAL_SHELL = ("bash", "--login")
"""The command that a terminal session runs."""

TERMINAL_TICKET_TIMEOUT = 60
"""Seconds within which a terminal ticket must be redeemed by opening the WebSocket."""

TERMINAL_IDLE_TIMEOUT = 30 * 60
"""Seconds without input after which a terminal session is ended."""

TERMINAL_MAX_DURATION = 8 * 60 * 60
"""Seconds after which a terminal session is ended, with or without input."""

TERMINAL_WATCHDOG_INTERVAL = 15
"""Seconds between the checks of a terminal session's idle time and duration."""

TERMINAL_MAX_SESSIONS = 8
"""The most terminal sessions that one server process runs at a time."""

TERMINAL_READ_SIZE = 64 * 1024
"""The most bytes read from a terminal at a time, and so sent in one WebSocket message."""

TERMINAL_MAX_QUEUED_READS = 64
"""Reads waiting to be sent, past which the terminal is no longer read until the browser catches up."""

TERMINAL_TERMINATE_GRACE = 2.0
"""Seconds that a hung up shell has to exit before its processes are killed."""
