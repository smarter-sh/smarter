"""
Custom logging handlers for the Smarter application.

This module provides a custom logging handler, :class:`StreamingFileHandler`, which writes log records
to a file in real-time. This is useful for capturing logs for individual jobs or processes, especially
when logs need to be streamed or persisted separately from the main application log.

Classes
-------
StreamingFileHandler
    A logging handler that writes log records to a temporary file, one per job.

Examples
--------
To use the streaming file handler in your logging configuration::

    import logging
    from smarter.lib.logging.streaming_file_handler import StreamingFileHandler

    handler = StreamingFileHandler(job_id="my-job-123")
    logger = logging.getLogger("my_job_logger")
    logger.addHandler(handler)
    logger.info("This log will be written to a job-specific file.")

The log file will be created in the system temporary directory under a "logs" subdirectory.
"""

import logging
import os
import tempfile


class StreamingFileHandler(logging.Handler):
    """
    Logging handler that writes log records to a job-specific file in real-time.

    This handler creates (or appends to) a log file in the system temporary directory under a
    "logs" subdirectory. Each handler instance writes to a file named after the provided job ID.
    Log records are formatted and written immediately as they are emitted.

    Parameters
    ----------
    job_id : str
        Unique identifier for the job or process. Used as the log file name (e.g., ``<job_id>.log``).

    Attributes
    ----------
    path : str
        The full path to the log file where records are written.

    Examples
    --------
    >>> handler = StreamingFileHandler(job_id="my-job-123")
    >>> import logging
    >>> logger = logging.getLogger("my_job_logger")
    >>> logger.addHandler(handler)
    >>> logger.info("This log will be written to a job-specific file.")

    The log file will be created in the system temporary directory under a "logs" subdirectory.
    """

    def __init__(self, job_id):
        super().__init__()
        log_dir = os.path.join(tempfile.gettempdir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, f"{job_id}.log")

    def emit(self, record):
        """
        Write a log record to the job-specific log file.

        This method is called by the logging framework for each log record. It formats the record
        using the handler's formatter and appends it to the log file associated with this handler's job ID.
        The log file is opened in append mode and flushed after each write to ensure real-time streaming.

        Parameters
        ----------
        record : logging.LogRecord
            The log record to be written to the file. This object contains all information about the event being logged.

        Notes
        -----
        If the log file or directory does not exist, it will be created automatically. The file is opened
        in UTF-8 encoding and each log entry is written on a new line.

        Examples
        --------
        This method is typically called by the logging framework and not used directly.
        """
        log_entry = self.format(record)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            f.flush()


__all__ = [
    "StreamingFileHandler",
]
