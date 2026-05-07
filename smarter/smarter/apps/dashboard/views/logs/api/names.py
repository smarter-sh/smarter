"""
URLs for the logs views.
"""

from smarter.common.utils import camel_case_object_name

from .const import namespace
from .streams import stream_user_logs


class DashboardLogsApiReverseNames:
    """
    A class to hold the names of the logs views for easy reference throughout the codebase.
    """

    namespace = namespace

    stream = camel_case_object_name(stream_user_logs)
