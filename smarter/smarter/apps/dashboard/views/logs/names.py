"""
URLs for the logs views.
"""

from smarter.common.utils import camel_case_object_name

from .const import namespace
from .consumers import RedisLogConsumer
from .reactapp import TerminalEmulatorLogView
from .streams import stream_user_logs


class DashboardLogsReverseNames:
    """
    A class to hold the names of the logs views for easy reference throughout the codebase.
    """

    namespace = namespace

    logs = camel_case_object_name(TerminalEmulatorLogView)
    stream = camel_case_object_name(stream_user_logs)
    consumer = camel_case_object_name(RedisLogConsumer)
