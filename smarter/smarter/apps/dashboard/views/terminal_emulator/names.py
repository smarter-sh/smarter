"""Reverse names for the server logs and terminal views."""

from smarter.common.utils import to_snake_case

from .api.tickets import TerminalTicketApiView
from .const import namespace, terminal_namespace
from .reactapp import TerminalEmulatorView


class DashboardLogsReverseNames:
    """A class to hold the names of the logs views for easy reference throughout the codebase."""

    namespace = namespace


class DashboardTerminalReverseNames:
    """The names of the Terminal page and its ticket api."""

    namespace = terminal_namespace

    terminal_emulator_view = to_snake_case(TerminalEmulatorView.__name__)
    ticket = to_snake_case(TerminalTicketApiView.__name__)
