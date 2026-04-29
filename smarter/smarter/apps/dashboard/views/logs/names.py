"""
URLs for the logs views.
"""

from smarter.apps.dashboard.const import namespace as dashboard_namespace
from smarter.common.utils import camel_case_object_name

from .const import namespace as logs_namespace
from .consumers import RedisLogConsumer
from .reactapp import TerminalEmulatorLogView
from .streams import stream_global_logs


class LogsNames:
    """
    A class to hold the names of the logs views for easy reference throughout the codebase.
    """

    namespace = ":".join([dashboard_namespace, logs_namespace])

    logs = camel_case_object_name(TerminalEmulatorLogView)
    stream = camel_case_object_name(stream_global_logs)
    consumer = camel_case_object_name(RedisLogConsumer)
