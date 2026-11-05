"""Reverse names for the server log stream and the terminal's ticket api, in the web console's api."""

from smarter.apps.api.web.const import path_namespace
from smarter.apps.dashboard.const import namespace as dashboard_namespace
from smarter.apps.dashboard.views.terminal_emulator.api.streams import stream_user_logs
from smarter.apps.dashboard.views.terminal_emulator.api.tickets import (
    TerminalTicketApiView,
)
from smarter.apps.dashboard.views.terminal_emulator.const import (
    namespace,
    terminal_namespace,
)
from smarter.common.utils import to_snake_case


class DashboardLogsApiReverseNames:
    """
    Reverse view names for the server log stream, at ``/api/web/dashboard/logs/``.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(DashboardLogsApiReverseNames.namespace, DashboardLogsApiReverseNames.stream)
    """

    namespace = f"{path_namespace}:{dashboard_namespace}:{namespace}"

    stream = to_snake_case(stream_user_logs.__name__)


class DashboardTerminalApiReverseNames:
    """
    Reverse view names for the terminal's ticket api, at ``/api/web/dashboard/terminal/``.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(DashboardTerminalApiReverseNames.namespace, DashboardTerminalApiReverseNames.ticket)
    """

    namespace = f"{path_namespace}:{dashboard_namespace}:{terminal_namespace}"

    ticket = to_snake_case(TerminalTicketApiView.__name__)
