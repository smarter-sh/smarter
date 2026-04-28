"""
Overridden logging module to add custom log handlers.
"""

import logging
import os
import tempfile


class StreamingFileHandler(logging.Handler):
    """
    Custom logging handler that writes log records to a file in real-time.
    """

    def __init__(self, job_id):
        super().__init__()
        log_dir = os.path.join(tempfile.gettempdir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, f"{job_id}.log")

    def emit(self, record):
        log_entry = self.format(record)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            f.flush()


__all__ = [
    "StreamingFileHandler",
]
