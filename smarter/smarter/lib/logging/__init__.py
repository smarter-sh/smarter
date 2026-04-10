"""
A logger that can be controlled with a condition function.
This allows for more flexible logging behavior based on runtime conditions.
"""

from .redis_log_handler import RedisLogHandler, current_job_id, job_id_factory
from .streaming_file_handler import StreamingFileHandler
from .waffle_switched_logger import WaffleSwitchedLoggerWrapper

__all__ = [
    "WaffleSwitchedLoggerWrapper",
    "current_job_id",
    "job_id_factory",
    "StreamingFileHandler",
    "RedisLogHandler",
]
