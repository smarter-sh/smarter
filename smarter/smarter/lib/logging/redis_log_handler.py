"""
smarter.lib.logging.redis_log_handler
=====================================

This module provides a custom logging handler for publishing log records to Redis channels,
enabling real-time log streaming for distributed systems. It is designed to work with context-aware
job IDs, allowing logs to be associated with specific jobs or tasks (such as Celery tasks), as well as
to a global log channel for system-wide log aggregation.

This handler is used for the Terminal Emulator real-time log view in the Smarter
web console.

Main Components
---------------

- ``smarter.lib.logging.redis_log_handler.RedisLogHandler``: A custom logging handler that publishes log records to Redis channels, supporting both job-specific and global log streams.
- ``smarter.lib.logging.redis_log_handler.job_id_factory``: Utility function to generate unique job IDs for associating logs with specific jobs or tasks.
- ``smarter.lib.logging.redis_log_handler.user_id_context``: Context variable for tracking the current job ID within the logging context.
- ``smarter.lib.logging.redis_log_handler.GLOBAL_LOG_CHANNEL``: The Redis channel name used for publishing all logs globally.

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
            }

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
    from smarter.lib.logging.redis_log_handler import RedisLogHandler, user_id_context, job_id_factory

    # Set the current job ID (typically in a Celery task or similar context)
    user_id_context.set(job_id_factory("task"))

    # Configure the logger
    logger = logging.getLogger("my_logger")
    logger.setLevel(logging.INFO)
    logger.addHandler(RedisLogHandler())

    logger.info("This log will be published to Redis.")

"""

import atexit
import os
import queue
import threading
import uuid
from contextvars import ContextVar
from typing import Any, Union

from django.core.exceptions import ImproperlyConfigured
from django_redis import get_redis_connection

from smarter.lib import json, logging

CONTEXT_NAME = "user_id"
CHANNEL_PREFIX = "logs"
GLOBAL_LOG_CHANNEL = "global"
MAX_BATCH = 100
MAX_QUEUE_SIZE = 10000
LOG_QUEUE_TIMEOUT = 0.05
WORKER_QUEUE_TIMEOUT = 1.00

USER_STREAM_TTL_SECONDS = (
    60 * 60 * 24
)  # one day default for user streams since they are typically lower volume and may be useful for debugging over a longer time horizon.
GLOBAL_STREAM_TTL_SECONDS = (
    60 * 60 * 1
)  # one hour default for global stream since it's typically higher volume and used for short-term UI feed rather than long-term storage.

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

_redis_cache_holder = {"client": None}
user_id_context: ContextVar[str | None] = ContextVar(CONTEXT_NAME, default=None)
log_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)


def redis_is_ready() -> bool:
    """Check if the Redis cache is ready to accept connections."""
    cache = get_redis_cache()
    if cache is None:
        return False
    try:
        cache.ping()
        return True
    # pylint: disable=broad-except
    except Exception:
        logger.warning(
            "%s.redis_is_ready() Redis cache is not responding. Logs will not be published to Redis.", logger_prefix
        )
        return False


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


def build_channel(name: str) -> str:
    """Build a normalized Redis pubsub channel name."""
    return f"{CHANNEL_PREFIX}:{name}"


def stream_key(channel: str) -> str:
    """Build the Redis stream key for a pubsub channel."""
    return f"stream:{channel}"


def stream_ttl_seconds(channel: str) -> int | None:
    """Return TTL policy for a channel stream key."""
    if channel == build_channel(GLOBAL_LOG_CHANNEL):
        return GLOBAL_STREAM_TTL_SECONDS
    return USER_STREAM_TTL_SECONDS


def get_user_channel() -> str:
    """
    Return the current user channel suffix from context.

    This value is expected to be a stable user identity string
    (for example "User.123") and is reused across requests for
    that same user.
    """
    return user_id_context.get() or job_id_factory()


def get_user_context(user: Any) -> str:
    """
    Retrieves the current user context for logging.

    This function accesses the :obj:`user_id_context` context variable to get the current user ID or job ID
    associated with the logging context. This is used by the :obj:`RedisLogHandler` to determine which Redis
    channel to publish log records to, allowing for both job-specific and global log streams.

    :return: The current user context (user ID or job ID) for logging.
    :rtype: str
    """
    # pylint: disable=C0415
    from smarter.apps.account.models import get_resolved_user

    user = get_resolved_user(user)
    return f"{user.__class__.__name__}.{user.username}"


def get_redis_cache() -> Any:
    """
    Lazily retrieves the configured Redis cache connection.

    During early process startup (for example management command bootstrap),
    Django settings may not yet be configured. In that case this returns None
    and callers should safely skip publishing.
    """
    cached_client = _redis_cache_holder["client"]
    if cached_client is not None:
        return cached_client

    try:
        _redis_cache_holder["client"] = get_redis_connection("default")
    except ImproperlyConfigured:
        logger.warning(
            "%s.get_redis_cache() Redis cache is not configured. Logs will not be published to Redis.", logger_prefix
        )
        return None
    return _redis_cache_holder["client"]


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
    if not redis_is_ready():
        for _ in buffer:
            log_queue.task_done()
        return

    cache = get_redis_cache()
    if cache is None:
        for _ in buffer:
            log_queue.task_done()
        return

    pipe = cache.pipeline()
    for payload in buffer:
        channel = payload["channel"]
        key = stream_key(channel)
        pipe.publish(channel, payload["data"])
        pipe.xadd(key, {"data": payload["data"]})
        ttl = stream_ttl_seconds(channel)
        if ttl is not None:
            pipe.expire(key, ttl)
        log_queue.task_done()
    try:
        pipe.execute()
    # pylint: disable=broad-except
    except Exception:
        logger.exception("%s.flush() Failed to execute Redis pipeline.", logger_prefix, exc_info=True)


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
    if not redis_is_ready():
        logger.warning(
            "%s.redis_worker() Redis cache is not ready. Redis log worker thread will not start.", logger_prefix
        )
        return

    logger.debug("%s.redis_worker() Starting Redis log worker thread.", logger_prefix)
    buffer = []

    while True:
        try:
            item = log_queue.get(timeout=LOG_QUEUE_TIMEOUT)
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
            flush(buffer)
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
    if not worker_thread.is_alive():
        return
    if not redis_is_ready():
        return
    try:
        log_queue.put_nowait(None)
    except queue.Full:
        logger.exception(
            "%s.shutdown() Failed to signal Redis log worker thread for shutdown.", logger_prefix, exc_info=True
        )
    worker_thread.join(timeout=WORKER_QUEUE_TIMEOUT)


# Register the shutdown function to be called when the process exits, ensuring
# that the worker thread is signaled to stop and any remaining logs are flushed.
atexit.register(shutdown)


class RedisLogHandler(logging.Handler):
    """
    Custom logging handler that publishes log records to Redis channels for real-time log streaming.

    This handler supports both job-specific and global log channels:

    - If a job ID is present in the :obj:`user_id_context` context variable, the log record is published to
        the Redis channel ``logs:{user_id}``, where ``{user_id}`` is the unique identifier for the job or task.
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
    user_id_context : Context variable for the current job ID.
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
        user_id = get_user_channel()

        try:
            # Respect Django logging formatter configuration (e.g. asctime/levelname)
            # for Redis-streamed log output.
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
            log_queue.put_nowait(
                {
                    "channel": build_channel(user_id),
                    "data": data,
                }
            )

            # Publish the log entry to a global Redis channel
            # for all logs. This is the feed for the optional
            # 'server logs' view in the UI, which shows
            # all log output.
            log_queue.put_nowait(
                {
                    "channel": build_channel(GLOBAL_LOG_CHANNEL),
                    "data": data,
                }
            )

        except queue.Full:
            RedisLogHandler.dropped_logs += 1
            if RedisLogHandler.dropped_logs % 100 == 0:
                print(f"Dropped {RedisLogHandler.dropped_logs} logs")
        # pylint: disable=broad-except
        except Exception:
            logger.exception("%s.emit() Failed to emit log record.", logger_prefix, exc_info=True)


__all__ = [
    "get_user_context",
    "GLOBAL_LOG_CHANNEL",
    "user_id_context",
    "RedisLogHandler",
    "job_id_factory",
]
