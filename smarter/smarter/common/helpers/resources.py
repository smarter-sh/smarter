"""
Helpers that compare a container's CPU and memory limits with what its server needs.

Uvicorn's ``--workers`` starts each worker with :mod:`multiprocessing`'s spawn method,
so each one imports all of Django on its own and shares no memory with the others. A
container's needs therefore grow with its worker count, and the recommendations here
are computed from it rather than fixed.

The figures come from measurement: one uvicorn worker uses about 420 MB at rest (see
``app.workers`` in ``helm/charts/smarter/values.yaml``), and runs Python on at most one
core at a time. Celery's prefork pool forks its children from a process that has
already loaded Django, so they share most of that memory, and a Celery container counts
as a single process here.

This module uses only the standard library, so that it can run while Django's settings
are being loaded.
"""

import logging
import math
import multiprocessing
import os
from typing import Optional

from smarter.common.helpers.processes import is_first_worker

#: Memory, in GiB, to recommend for each uvicorn worker: about 420 MB at rest, plus the
#: threads and buffers of the requests it has in flight.
MEMORY_GIB_PER_WORKER = 0.5

#: Memory, in GiB, to recommend on top of the workers' share, for the server's parent
#: process and short spikes.
MEMORY_HEADROOM_GIB = 0.5

CGROUP_CPU_MAX = "/sys/fs/cgroup/cpu.max"
CGROUP_MEMORY_MAX = "/sys/fs/cgroup/memory.max"
PROC_MEMINFO = "/proc/meminfo"


def cpu_limit() -> int:
    """
    Return the number of cores this container may use, rounded up.

    Reads the cgroup v2 quota, and falls back to the cores this process may run on when
    the container has no CPU limit or isn't in a cgroup v2.

    :returns: The number of cores.
    """
    if os.path.exists(CGROUP_CPU_MAX):
        with open(CGROUP_CPU_MAX, encoding="utf-8") as f:
            quota, period = f.read().strip().split()
        if quota != "max":
            return math.ceil(int(quota) / int(period))
    # os.process_cpu_count() (Python 3.13+) counts the cores this process may run on.
    available_cores = getattr(os, "process_cpu_count", os.cpu_count)
    return available_cores() or 1


def memory_limit_gib() -> float:
    """
    Return the memory, in GiB, that this container may use.

    Reads the cgroup v2 limit, and falls back to the host's total memory when the
    container has no memory limit or isn't in a cgroup v2.

    :returns: The memory limit in GiB.
    """
    if os.path.exists(CGROUP_MEMORY_MAX):
        with open(CGROUP_MEMORY_MAX, encoding="utf-8") as f:
            memory_max = f.read().strip()
        if memory_max != "max":
            return int(memory_max) / 1024**3
    with open(PROC_MEMINFO, encoding="utf-8") as f:
        for line in f:
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024**2
    raise ValueError(f"MemTotal not found in {PROC_MEMINFO}")


def workers_from_command_line(args: list[str]) -> Optional[int]:
    """
    Return the value of uvicorn's ``--workers`` option in a command line.

    :param args: The command line, split into arguments.
    :returns: The worker count, or None if the command line has no ``--workers``.
    """
    for i, arg in enumerate(args):
        if arg.startswith("--workers="):
            return int(arg.split("=", 1)[1])
        if arg == "--workers" and i + 1 < len(args):
            return int(args[i + 1])
    return None


def uvicorn_workers() -> int:
    """
    Return the number of uvicorn workers that share this container.

    A uvicorn worker is a spawned child of the uvicorn process, so the count is read from
    the ``--workers`` option of the parent's command line, then from ``WEB_CONCURRENCY``,
    which uvicorn reads when ``--workers`` is absent. Any other process, such as uvicorn
    without ``--workers``, a Celery worker or ``manage.py``, counts as one.

    :returns: The number of workers, at least 1.
    """
    if multiprocessing.parent_process() is None:
        return 1
    try:
        with open(f"/proc/{os.getppid()}/cmdline", encoding="utf-8") as f:
            args = [arg for arg in f.read().split("\0") if arg]
        workers = workers_from_command_line(args)
    except (OSError, ValueError):
        workers = None
    if workers is None:
        try:
            workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
        except ValueError:
            workers = 1
    return max(workers, 1)


def recommended_cpu(workers: int) -> int:
    """
    Return the CPU limit to recommend for a server, one core per worker.

    :param workers: The number of uvicorn workers.
    :returns: The recommended number of cores.
    """
    return max(workers, 1)


def recommended_memory_gib(workers: int) -> float:
    """
    Return the memory limit, in GiB, to recommend for a server.

    :param workers: The number of uvicorn workers.
    :returns: ``workers`` times :data:`MEMORY_GIB_PER_WORKER`, plus :data:`MEMORY_HEADROOM_GIB`.
    """
    return max(workers, 1) * MEMORY_GIB_PER_WORKER + MEMORY_HEADROOM_GIB


def log_resource_limits(logger: logging.Logger, prefix: str) -> None:
    """
    Log this container's CPU and memory limits, and warn when they are below what its server needs.

    The limits are logged at DEBUG by every process. A warning is logged by one uvicorn
    worker per server (see :func:`~smarter.common.helpers.processes.is_first_worker`),
    since its workers share the container and would otherwise each log the same warning.

    :param logger: The logger to write to.
    :param prefix: The prefix that starts each message, e.g. the caller's ``logger_prefix``.
    """
    try:
        cpu = cpu_limit()
        memory = memory_limit_gib()
    except OSError as e:
        logger.warning("%s.log_resource_limits() resource limits not available: %s", prefix, e)
        return
    except (ValueError, IndexError) as e:
        logger.error("%s.log_resource_limits() error parsing resource limits: %s", prefix, e)
        return

    workers = uvicorn_workers()
    min_cpu = recommended_cpu(workers)
    min_memory = recommended_memory_gib(workers)
    logger.debug(
        "%s.log_resource_limits() CPU limit: %s cores, memory limit: %.2f GiB, uvicorn workers: %s",
        prefix,
        cpu,
        memory,
        workers,
    )
    if (cpu >= min_cpu and memory >= min_memory) or not is_first_worker("resource-limits"):
        return
    if cpu < min_cpu:
        logger.warning(
            "%s.log_resource_limits() recommended minimum CPU limit for %s uvicorn worker(s) is %s. Detected: %s cores",
            prefix,
            workers,
            min_cpu,
            cpu,
        )
    if memory < min_memory:
        logger.warning(
            "%s.log_resource_limits() recommended minimum memory limit for %s uvicorn worker(s) is %.2f GiB. "
            "Detected: %.2f GiB",
            prefix,
            workers,
            min_memory,
            memory,
        )


__all__ = [
    "MEMORY_GIB_PER_WORKER",
    "MEMORY_HEADROOM_GIB",
    "cpu_limit",
    "log_resource_limits",
    "memory_limit_gib",
    "recommended_cpu",
    "recommended_memory_gib",
    "uvicorn_workers",
    "workers_from_command_line",
]
