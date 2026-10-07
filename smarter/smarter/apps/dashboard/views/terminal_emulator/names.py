"""Reverse names for the logs views."""

from smarter.common.utils import to_snake_case

from .const import namespace
from .reactapp import TerminalEmulatorLogView


class DashboardLogsReverseNames:
    """A class to hold the names of the logs views for easy reference throughout the codebase."""

    namespace = namespace

    terminal_emulator_view = to_snake_case(TerminalEmulatorLogView.__name__)
