"""
Close the database connections of a thread that does Django work outside a request.

Django opens a database connection per thread on first use, and closes it when a request starts
and when it finishes, in the thread that handles the request. Work that runs in another thread
never sees those signals: a thread of the event loop's default executor, where
``sync_to_async(..., thread_sensitive=False)`` runs, or a thread of a ``ThreadPoolExecutor``.
A connection that such work opens stays open, idle, for as long as the thread lives, and the
next work that runs in the same thread reuses it. Once the database server has closed it, e.g.
after MariaDB's ``wait_timeout`` (8 hours) or a restart, that work fails with
``(2006, "MySQL server has gone away")``.

Work that runs outside a request closes its thread's connections when it finishes, with
:func:`close_thread_connections`.
"""

from django.db import connections


def close_thread_connections() -> None:
    """
    Close every database connection that the current thread has opened.

    Call it in a ``finally`` block at the end of work that runs in a thread outside the request
    cycle. Django opens a new connection the next time the thread queries the database.

    A connection inside a transaction (an ``atomic`` block) is left open, so that work called
    from a test's or a caller's transaction doesn't break it.
    """
    for connection in connections.all(initialized_only=True):
        if not connection.in_atomic_block:
            connection.close()


__all__ = ["close_thread_connections"]
