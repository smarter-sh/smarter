"""
Helpers for code that runs once in each of a server's worker processes.

Uvicorn's ``--workers`` imports the application once per worker process, so anything
that runs at import time, such as the startup banner or the settings' READY message,
runs once per worker. :func:`is_first_worker` lets that code run in only one of them.

This module uses only the standard library, so that :mod:`smarter.common.conf.settings`
can import it before Django is set up.
"""

import multiprocessing
import os
import tempfile


def is_first_worker(name: str) -> bool:
    """
    Return whether this process is the first of its server's workers to ask, for ``name``.

    A process that wasn't started by :mod:`multiprocessing`, such as ``uvicorn`` without
    ``--workers``, a Celery worker or ``manage.py``, is always the first. Uvicorn's workers
    are its children, and share a parent pid, so the first of them to create a marker file
    named for ``name`` and that pid is the first. Each ``name`` has its own marker, so the
    question can be asked once for each thing that should happen once.

    :param name: What should happen once per server, e.g. ``startup-banner``. It becomes
        part of a file name.
    :returns: True if this process is the first, or if the marker file can't be created.
    """
    if multiprocessing.parent_process() is None:
        return True
    marker = os.path.join(tempfile.gettempdir(), f"smarter-{name}-{os.getppid()}")
    try:
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    except OSError:
        return True
    os.close(fd)
    return True


__all__ = ["is_first_worker"]
