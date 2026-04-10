"""
Overridden logging module to add custom log handlers.
"""

import contextvars
import logging
import uuid

import redis

from smarter.lib import json

r = redis.Redis(host="localhost", port=6379, db=0)
current_job_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("job_id", default=None)


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
    Custom logging handler that publishes log records to Redis channels
    for real-time log streaming to clients. Each log record is published
    to a Redis channel named "logs:{job_id}", where {job_id} is the
    unique identifier for the job or task associated with the log record.

    This handler is designed to work with the `current_job_id` context
    variable, which should be set to a unique job ID before logging.
    current_job_id is set from the Celery task using the job_id_factory
    and is assumed to be set to the Celery task ID for tasks.

    When a log record is emitted, the handler checks for the presence of
    a job ID in the context. If a job ID is found, the log record is
    formatted and published to the corresponding Redis channel. If no job
    ID is found, the log record is ignored.
    """

    def emit(self, record):
        job_id = current_job_id.get()

        if not job_id:
            return  # ignore logs not tied to a job

        try:
            log_entry = self.format(record)

            payload = {
                "message": log_entry,
                "level": record.levelname,
                "timestamp": record.created,
            }

            r.publish(f"logs:{job_id}", json.dumps(payload))
        # pylint: disable=broad-except
        except Exception:
            pass


__all__ = [
    "current_job_id",
    "RedisLogHandler",
    "job_id_factory",
]
