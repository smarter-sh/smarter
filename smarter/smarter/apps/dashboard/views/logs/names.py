"""
Reverse names for the logs views.
"""

from smarter.common.utils import camel_case_object_name

from .const import namespace
from .reactapp import TerminalEmulatorLogView


class DashboardLogsReverseNames:
    """
    A class to hold the names of the logs views for easy reference throughout the codebase.
    """

    namespace = namespace

    terminal_emulator_view = camel_case_object_name(TerminalEmulatorLogView)
