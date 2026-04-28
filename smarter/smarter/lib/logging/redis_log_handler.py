"""
smarter.lib.logging.redis_log_handler
=====================================

This module provides a custom logging handler for publishing log records to Redis channels,
enabling real-time log streaming for distributed systems. It is designed to work with context-aware
job IDs, allowing logs to be associated with specific jobs or tasks (such as Celery tasks), as well as
to a global log channel for system-wide log aggregation.

Main Components
---------------

- ``RedisLogHandler``: A custom logging handler that publishes log records to Redis channels, supporting both job-specific and global log streams.
- ``job_id_factory``: Utility function to generate unique job IDs for associating logs with specific jobs or tasks.
- ``current_job_id``: Context variable for tracking the current job ID within the logging context.
- ``GLOBAL_LOG_CHANNEL``: The Redis channel name used for publishing all logs globally.

Features
--------

- Asynchronous log publishing to Redis using a background worker thread and batching for efficiency.
- Support for both job-specific and global log channels.
- Graceful shutdown and log flushing on process exit.
- Handles dropped logs if the internal queue is full, with periodic reporting.

Example Usage
-------------

.. code-block:: python

        #
        # configure the Django logging to use the RedisLogHandler
        #
        LOGGING = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "timestamped": {
                    "format": "%(asctime)s - %(levelname)s - %(processName)s - %(message)s",
                    "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
                },
            },
            "handlers": {
                "default": {
                    "level": smarter_settings.log_level_name,
                    "class": "logging.StreamHandler",
                    "formatter": "timestamped",
                },
                "redis": {
                    "level": smarter_settings.log_level_name,
                    "class": "smarter.lib.logging.RedisLogHandler",  # <--- Use the RedisLogHandler
                    "formatter": "timestamped",
                },
            },
            "root": {
                "handlers": ["default", "redis"],  # <--- Add the RedisLogHandler to the root logger
                "level": smarter_settings.log_level_name,
            },

.. attention::

    The following is technically possible but not a recommended practice.
    It demonstrates how to manually configure logging to use the RedisLogHandler
    outside of a Django settings context, such as in a standalone script or a
    Celery task. In most cases, it's better to configure logging through the
    Django settings for consistency and maintainability.

.. code-block:: python

    #
    # manually configure logging to use RedisLogHandler
    # NOTE: this is technically possible but not a great idea.
    #
    import logging
    from smarter.lib.logging.redis_log_handler import RedisLogHandler, current_job_id, job_id_factory

    # Set the current job ID (typically in a Celery task or similar context)
    current_job_id.set(job_id_factory("task"))

    # Configure the logger
    logger = logging.getLogger("my_logger")
    logger.setLevel(logging.INFO)
    logger.addHandler(RedisLogHandler())

    logger.info("This log will be published to Redis.")

"""

import atexit
import contextvars
import logging
import os
import queue
import threading
import uuid

import redis

from smarter.lib import json

GLOBAL_LOG_CHANNEL = "logs:global"
MAX_BATCH = 100


r = redis.Redis(host="localhost", port=6379, db=0)
current_job_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("job_id", default=None)
log_queue = queue.Queue(maxsize=10000)


def flush(buffer) -> None:
    """
    Flushes the buffer of log entries to Redis.

    This function takes a list of log entries (buffer) and publishes each
    entry to its corresponding Redis channel using a pipeline for
    efficiency. After publishing, it marks each entry as done in the
    log queue.

    :param buffer: List of log entries to be published.
    :type buffer: list
    :return: None
    """
    pipe = r.pipeline()
    for payload in buffer:
        pipe.publish(payload["channel"], payload["data"])
        log_queue.task_done()
    try:
        pipe.execute()
    # pylint: disable=broad-except
    except Exception:
        pass


def redis_worker() -> None:
    """
    Worker function that continuously processes log entries from the queue
    and publishes them to Redis channels. This function runs in a separate
    thread and handles batching of log entries for efficiency.

    The worker retrieves log entries from the queue, batches them up to a
    maximum size defined by MAX_BATCH, and then flushes the batch to Redis.
    If the queue is empty, it waits briefly before checking again. The worker
    also listens for a sentinel value (None) to gracefully shut down when
    the process is exiting.

    :param None: No parameters are required for this function.
    :return: None
    """
    buffer = []

    while True:
        try:
            item = log_queue.get(timeout=0.05)
            if item is None:
                log_queue.task_done()
                break
            buffer.append(item)
            if len(buffer) >= MAX_BATCH:
                flush(buffer)
                buffer.clear()
        except queue.Empty:
            pass

        if buffer:
            pipe = r.pipeline()

            for payload in buffer:
                pipe.publish(payload["channel"], payload["data"])
                log_queue.task_done()

            try:
                pipe.execute()
            # pylint: disable=broad-except
            except Exception:
                pass

            buffer.clear()


# Module-level background thread for asynchronous Redis log publishing.
# This thread runs the redis_worker function as a daemon to process
# and publish log entries from the queue.
worker_thread = threading.Thread(target=redis_worker, daemon=True)
worker_thread.start()


def shutdown() -> None:
    """
    Gracefully shuts down the Redis log worker thread.

    This function attempts to signal the worker thread to exit by
    placing a sentinel value (None) in the log queue. It then waits
    for the worker thread to finish processing any remaining log
    entries, with a timeout of 1 second.

    :param None: No parameters are required for this function.
    :return: None
    """
    try:
        log_queue.put_nowait(None)
    except queue.Full:
        pass
    worker_thread.join(timeout=1)


# Register the shutdown function to be called when the process exits, ensuring
# that the worker thread is signaled to stop and any remaining logs are flushed.
atexit.register(shutdown)


def job_id_factory(prefix: str = "job") -> str:
    """
    Factory method to generate a unique job ID.

    This method creates a unique identifier for jobs or tasks, using
    a specified prefix and a random UUID. The resulting ID is
    formatted as "{prefix}_{uuid}". This is used primarily for
    managing subscriptions to Server-Sent Events (SSE) channels,
    for ensuring that each subscription has a unique identifier.

    :param prefix: The prefix to use for the job ID (default is "job").
    :type prefix: str
    :return: A unique job ID string.
    :rtype: str
    """
    return f"{prefix}_{str(uuid.uuid4())}"


class RedisLogHandler(logging.Handler):
    """
    Custom logging handler that publishes log records to Redis channels for real-time log streaming.

    This handler supports both job-specific and global log channels:

    - If a job ID is present in the :obj:`current_job_id` context variable, the log record is published to
        the Redis channel ``logs:{job_id}``, where ``{job_id}`` is the unique identifier for the job or task.
    - All log records are also published to the global channel defined by :obj:`GLOBAL_LOG_CHANNEL` (``logs:global``),
        which can be used for system-wide log aggregation or UI log feeds.

    The handler is designed to be used in distributed or asynchronous environments (e.g., Celery tasks),
    where each job or task can have its own log stream. Log records are enqueued and published asynchronously
    by a background worker thread for efficiency and non-blocking behavior.

    If the internal log queue is full, log records may be dropped. The number of dropped logs is tracked by
    the class variable dropped_logs, and a message is printed every 100 dropped logs.


    See Also
    --------
    job_id_factory : Function to generate unique job IDs.
    current_job_id : Context variable for the current job ID.
    GLOBAL_LOG_CHANNEL : Name of the global Redis log channel.
    """

    dropped_logs = 0

    def emit(self, record):
        """
        Emit a log record.

        This method formats the log record and publishes it to the appropriate Redis channels.
        If a job ID is present in the current context, the log record is published to the job-specific
        channel. All log records are also published to the global log channel.

        :param record: The log record to be emitted.
        :type record: logging.LogRecord
        """
        job_id = current_job_id.get()

        try:
            log_entry = self.format(record)

            payload = {
                "message": log_entry,
                "level": record.levelname,
                "timestamp": record.created,
                "logger": record.name,
                "pod": os.getenv("HOSTNAME"),
            }

            data = json.dumps(payload)

            # Publish the log entry to the Redis channel for a
            # specific job ID. These are typically initiated
            # inside Celery tasks in cases where the log output
            # is viewable from the UI.
            #
            # enqueue instead of blocking
            if job_id:
                log_queue.put_nowait(
                    {
                        "channel": f"logs:{job_id}",
                        "data": data,
                    }
                )

            # Publish the log entry to a global Redis channel
            # for all logs. This is the feed for the optional
            # 'server logs' view in the UI, which shows
            # all log output.
            log_queue.put_nowait(
                {
                    "channel": GLOBAL_LOG_CHANNEL,
                    "data": data,
                }
            )

        except queue.Full:
            RedisLogHandler.dropped_logs += 1
            if RedisLogHandler.dropped_logs % 100 == 0:
                print(f"Dropped {RedisLogHandler.dropped_logs} logs")
        # pylint: disable=broad-except
        except Exception:
            pass


__all__ = [
    "GLOBAL_LOG_CHANNEL",
    "current_job_id",
    "RedisLogHandler",
    "job_id_factory",
]
