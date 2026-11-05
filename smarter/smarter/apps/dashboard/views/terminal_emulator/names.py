"""Reverse names for the Terminal page."""

from smarter.apps.dashboard.views.terminal_emulator.const import terminal_namespace
from smarter.apps.dashboard.views.terminal_emulator.reactapp import TerminalEmulatorView
from smarter.common.utils import to_snake_case


class DashboardTerminalReverseNames:
    """
    The names of the Terminal page.

    Its ticket api is in the web console's api: see
    :class:`smarter.apps.dashboard.views.terminal_emulator.api.names.DashboardTerminalApiReverseNames`.
    """

    namespace = terminal_namespace

    terminal_emulator_view = to_snake_case(TerminalEmulatorView.__name__)
