"""
Smarter.lib.logging.redis_log_handler
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
- ``smarter.lib.logging.redis_log_handler.request_id_context``: Context variable for the current request's id, which each published log record carries, so that a log stream can be narrowed to one request.
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
import re
import sys
import threading
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Callable, Optional, ParamSpec, TypeVar

from django.core.exceptions import ImproperlyConfigured
from django_redis import get_redis_connection

from smarter.lib import json, logging

if TYPE_CHECKING:
    from redis import Redis

CONTEXT_NAME = "user_id"
REQUEST_ID_CONTEXT_NAME = "request_id"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SESSION_KEY_CONTEXT_NAME = "session_key"
SESSION_KEY_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
"""
The form of a request id: up to 64 letters, digits, underscores and hyphens.

A request id is sent by the browser, in the ``X-Smarter-RequestId`` header, so it is validated
before it is attached to log records. See :func:`valid_request_id`.
"""
CHANNEL_PREFIX = "logs"
GLOBAL_LOG_CHANNEL = "global"
MAX_BATCH = 100
MAX_QUEUE_SIZE = 10000
LOG_QUEUE_TIMEOUT = 0.05
WORKER_QUEUE_TIMEOUT = 1.00

USER_STREAM_TTL_SECONDS = (
    1 * 60 * 60
)  # 1 hour for user/job-specific streams, which are expected to be consumed and then expire
GLOBAL_STREAM_TTL_SECONDS = (
    24 * 60 * 60
)  # 24 hours for the global stream, which is more of a firehose and may be consumed by multiple clients with different latencies

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

_redis_cache_holder = {"client": None}
_publish_state = {"failing": False}
"""Whether the last :func:`flush` failed, so that a Redis outage is logged once, not once per batch."""
user_id_context: ContextVar[str | None] = ContextVar(CONTEXT_NAME, default=None)
request_id_context: ContextVar[str | None] = ContextVar(REQUEST_ID_CONTEXT_NAME, default=None)
session_key_context: ContextVar[str | None] = ContextVar(SESSION_KEY_CONTEXT_NAME, default=None)
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


def valid_request_id(request_id: Optional[str]) -> Optional[str]:
    """
    Return a request id if it has the form of one, or else None.

    :param request_id: A request id, e.g. the value of a request's ``X-Smarter-RequestId`` header.
    :type request_id: Optional[str]
    :return: The request id, stripped, or None if it is missing or does not match
        :data:`REQUEST_ID_PATTERN`.
    :rtype: Optional[str]
    """
    if not request_id:
        return None
    request_id = request_id.strip()
    return request_id if REQUEST_ID_PATTERN.match(request_id) else None


def valid_session_key(session_key: Optional[str]) -> Optional[str]:
    """
    Return a chat session key if it has the form of one, or else None.

    :param session_key: A chat session key, e.g. the ``session_key`` query parameter of a
        request to an LLMClient's api.
    :type session_key: Optional[str]
    :return: The session key, stripped, or None if it is missing or does not match
        :data:`SESSION_KEY_PATTERN`.
    :rtype: Optional[str]
    """
    if not session_key:
        return None
    session_key = session_key.strip()
    return session_key if SESSION_KEY_PATTERN.match(session_key) else None


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
    if hasattr(user, "username"):
        username = user.username
    else:
        username = str(user)
    return f"{user.__class__.__name__}.{username}"


_P = ParamSpec("_P")
_T = TypeVar("_T")


def bind_log_context(func: Callable[_P, _T]) -> Callable[_P, _T]:
    """
    Return a function that calls ``func`` in the current log context.

    The log context is the user channel in :obj:`user_id_context`, the request id in
    :obj:`request_id_context` and the chat session key in :obj:`session_key_context`, which
    :class:`smarter.lib.logging.middleware.SmarterRequestLogContextMiddleware` sets for the
    duration of a request. Work that runs after the middleware returns, e.g. a streaming
    response's generator, runs without them, so its log records reach neither the user's log
    stream nor the request's. Bind such work while the request is being handled.

    :param func: The function to call in the current log context.
    :type func: Callable[_P, _T]
    :returns: A function that sets the log context, calls ``func`` and restores the log context
        that it found.
    :rtype: Callable[_P, _T]
    """
    user_id = user_id_context.get()
    request_id = request_id_context.get()
    session_key = session_key_context.get()

    def bound(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        user_token = user_id_context.set(user_id)
        request_token = request_id_context.set(request_id)
        session_token = session_key_context.set(session_key)
        try:
            return func(*args, **kwargs)
        finally:
            session_key_context.reset(session_token)
            request_id_context.reset(request_token)
            user_id_context.reset(user_token)

    return bound


def get_redis_cache() -> Optional["Redis"]:
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

    Redis isn't pinged first: that would cost a round trip per batch. When Redis is down,
    ``pipe.execute()`` fails, the batch is dropped, and the failure is logged once, until a
    batch is published again. Logging it on every batch would loop, because the exception's
    own log record is queued for the next batch.

    :param buffer: List of log entries to be published.
    :type buffer: list
    :return: None
    """
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
        pipe.xadd(key, {"data": payload["data"]}, maxlen=1000, approximate=True)
        ttl = stream_ttl_seconds(channel)
        if ttl is not None:
            pipe.expire(key, ttl)
        log_queue.task_done()
    try:
        pipe.execute()
    # pylint: disable=broad-except
    except Exception:
        if not _publish_state["failing"]:
            _publish_state["failing"] = True
            logger.exception(
                "%s.flush() Failed to execute Redis pipeline. Dropping log records until Redis is available.",
                logger_prefix,
                exc_info=True,
            )
        return
    if _publish_state["failing"]:
        _publish_state["failing"] = False
        logger.info("%s.flush() Redis is available again. Publishing log records.", logger_prefix)


def next_batch(timeout: float = LOG_QUEUE_TIMEOUT) -> tuple[list, bool]:
    """
    Take the next batch of log entries from the queue.

    Waits up to ``timeout`` seconds for one entry, then takes whatever else is
    already queued, without waiting, up to ``MAX_BATCH`` entries.

    :param timeout: Seconds to wait for the first entry.
    :type timeout: float
    :returns: The batch, which may be empty, and whether the shutdown sentinel (None) was taken.
    :rtype: tuple[list, bool]
    """
    buffer: list = []
    try:
        item = log_queue.get(timeout=timeout)
    except queue.Empty:
        return buffer, False
    while True:
        if item is None:
            log_queue.task_done()
            return buffer, True
        buffer.append(item)
        if len(buffer) >= MAX_BATCH:
            return buffer, False
        try:
            item = log_queue.get_nowait()
        except queue.Empty:
            return buffer, False


def purge_log_context(context: str):
    """Delete the Redis stream for a specific logging context."""
    cache = get_redis_cache()
    if cache is None:
        raise RuntimeError("Redis cache is not available")
    channel = build_channel(context)
    key = stream_key(channel)
    cache.delete(key)


def redis_worker() -> None:
    """
    Worker function that continuously processes log entries from the queue.

    and publishes them to Redis channels. This function runs in a separate
    thread and handles batching of log entries for efficiency.

    The worker takes everything that is queued, up to MAX_BATCH entries (see
    :func:`next_batch`), and publishes it to Redis in one pipeline. If the
    queue is empty, it waits briefly before checking again. The worker also
    listens for a sentinel value (None) to gracefully shut down when the
    process is exiting.

    :param None: No parameters are required for this function.
    :return: None
    """

    logger.debug("%s.redis_worker() Starting Redis log worker thread.", logger_prefix)

    while True:
        buffer, stop = next_batch()
        if buffer:
            flush(buffer)
        if stop:
            break


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
        channel. All log records are also published to the global log channel. While a request id is
        set in :obj:`request_id_context`, the record carries it as ``request_id``, and while a chat
        session key is set in :obj:`session_key_context`, as ``session_key``.

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
            request_id = request_id_context.get()
            if request_id:
                payload["request_id"] = request_id
            session_key = session_key_context.get()
            if session_key:
                payload["session_key"] = session_key

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
                # not logged: this handler's own log record would be queued, or dropped, too.
                print(
                    f"{logger_prefix}.RedisLogHandler.emit() the log queue is full: "
                    f"{RedisLogHandler.dropped_logs} log records were not published to Redis.",
                    file=sys.stderr,
                )
        # pylint: disable=broad-except
        except Exception:
            logger.exception("%s.emit() Failed to emit log record.", logger_prefix, exc_info=True)


__all__ = [
    "bind_log_context",
    "get_user_context",
    "GLOBAL_LOG_CHANNEL",
    "user_id_context",
    "request_id_context",
    "session_key_context",
    "valid_request_id",
    "valid_session_key",
    "RedisLogHandler",
    "job_id_factory",
]
