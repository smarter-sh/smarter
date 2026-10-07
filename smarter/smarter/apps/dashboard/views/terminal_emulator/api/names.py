"""URLs for the logs views."""

from smarter.common.utils import to_snake_case

from .const import namespace
from .streams import stream_user_logs


class DashboardLogsApiReverseNames:
    """A class to hold the names of the logs views for easy reference throughout the codebase."""

    namespace = namespace

    stream = to_snake_case(stream_user_logs.__name__)
