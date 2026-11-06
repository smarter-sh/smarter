"""
The liveness probe of a Smarter Celery worker: does the worker answer a ping, through the broker?

The Helm chart's worker Deployments run it as their ``livenessProbe``::

    python -m smarter.workers.liveness celery@$HOSTNAME
    python -m smarter.workers.liveness infrastructure@$HOSTNAME

A worker that is running is not necessarily working. After Redis restarted on another node, both
workers kept their processes, and so passed a probe that only looked for the process, but ran no
task, and logged nothing, until someone restarted them (issue #940). A ping travels the same way as
a task: it is published to Redis, and the worker reads it from its own broker connection and
answers. A worker that doesn't answer is stuck, and Kubernetes restarts it.

It imports neither Django nor the platform's tasks, so it starts in a fraction of a second and
uses little memory, every time the probe runs. It reads the broker's url from the
``CELERY_BROKER_URL`` environment variable, which every pod of the chart has.

.. code-block:: console

    $ python -m smarter.workers.liveness celery@smarter-worker-5b7f794fb-dw7mx
    celery@smarter-worker-5b7f794fb-dw7mx answered.
"""

import os
import sys
from typing import Optional

from celery import Celery

PING_TIMEOUT = 10.0
"""Seconds to wait for the worker's answer.

A busy worker answers between tasks, from its main process.
"""

DEFAULT_BROKER_URL = "redis://:smarter@smarter-redis:6379/0"
"""The broker of docker-compose, when ``CELERY_BROKER_URL`` is not set.

It is base.py's ``CELERY_BROKER_URL``.
"""


def broker_url() -> str:
    """
    Return the url of the Celery broker, from the ``CELERY_BROKER_URL`` environment variable.

    :returns: The url, or :data:`DEFAULT_BROKER_URL` if the variable is empty or not set.
    """
    url = os.environ.get("CELERY_BROKER_URL", "")
    if not url:
        return DEFAULT_BROKER_URL
    return url


def ping_worker(node_name: str, url: str, timeout: float = PING_TIMEOUT) -> bool:
    """
    Ping one Celery worker through the broker, and return whether it answered.

    Side effects: connects to the broker, publishes a ping to the worker, and waits up to
    ``timeout`` seconds for its answer.

    :param node_name: The worker's node name, e.g. ``celery@smarter-worker-5b7f794fb-dw7mx``.
    :param url: The broker's url.
    :param timeout: Seconds to wait for the answer.
    :returns: True if the worker answered.
    """
    app = Celery("smarter-liveness", broker=url)
    app.conf.broker_connection_retry_on_startup = False
    try:
        replies = app.control.ping(destination=[node_name], timeout=timeout)
    finally:
        app.close()
    if not replies:
        # Celery's stubs allow None, and an empty list means nobody answered.
        return False
    for reply in replies:
        if node_name in reply:
            return True
    return False


def main(argv: Optional[list[str]] = None) -> int:
    """
    Run the probe, and return its exit code.

    :param argv: The arguments: the worker's node name. Without it, ``celery@`` and the
        ``HOSTNAME`` environment variable, i.e. the pod's name.
    :returns: 0 if the worker answered, 1 if it didn't or the broker couldn't be reached.
    """
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        node_name = arguments[0]
    else:
        node_name = f"celery@{os.environ.get('HOSTNAME', '')}"
    try:
        answered = ping_worker(node_name, broker_url())
    # pylint: disable=broad-except
    except Exception as e:
        print(f"{node_name} could not be pinged: {type(e).__name__}: {e}")
        return 1
    if not answered:
        print(f"{node_name} did not answer a ping within {PING_TIMEOUT:g} seconds.")
        return 1
    print(f"{node_name} answered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
