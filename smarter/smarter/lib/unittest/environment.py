"""
The process environment that a test needs to build ``Settings`` as a restricted worker's.

The tests run in ``smarter-api``, whose environment holds the platform's credentials, from ``.env``, and its own
kind of pod, ``SERVICE_TYPE=api``. A test that builds ``Settings(database_unavailable=True)``, to stand in for the
tool worker or the Extension worker, would be refused twice: by
:meth:`~smarter.common.conf.settings.Settings.check_restricted_worker_credentials`, since a real restricted worker
is never given those credentials, and by :meth:`~smarter.common.conf.settings.Settings.check_service_type`, since
an api server has a database. :func:`as_restricted_worker` takes both out of the environment for the duration of
a ``with`` block, as a deployment never put them in a restricted worker's.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

from smarter.common.conf import Settings
from smarter.common.conf.credentials import (
    SecretBootstrapVariable,
    bootstrap_variable_names,
    environment_variables,
    is_credential,
    restricted_workers_may_hold,
)

SERVICE_TYPE_VARIABLE = "SERVICE_TYPE"
"""The environment variable of the kind of pod, which a test's stand-in worker sets itself, if at all."""


def forbidden_credential_variables() -> list[str]:
    """
    Return the environment variables of every credential that the restricted workers must not hold.

    Every credential setting's but their Redis password's, and every :class:`SecretBootstrapVariable`, which has no
    setting, with and without its prefix.

    :returns: The variables' names, e.g. ``SMARTER_APP_PROVIDER_OPENAI_API_KEY``.
    """
    retval: list[str] = []
    for name, field in Settings.model_fields.items():
        if not is_credential(field):
            continue
        if restricted_workers_may_hold(field):
            continue
        retval.extend(environment_variables(name, field))
    for bootstrap_name in SecretBootstrapVariable.all():
        retval.extend(bootstrap_variable_names(bootstrap_name))
    return retval


@contextmanager
def as_restricted_worker() -> Iterator[None]:
    """
    Make the environment, inside the ``with`` block, one that a restricted worker could have.

    It removes every credential that a restricted worker must not hold, and the test process's own kind of pod,
    ``SERVICE_TYPE``. The rest of the environment, and the Redis password that the restricted workers may hold,
    are left alone.
    """
    remaining = dict(os.environ)
    for variable in forbidden_credential_variables():
        remaining.pop(variable, None)
    remaining.pop(SERVICE_TYPE_VARIABLE, None)
    with patch.dict(os.environ, remaining, clear=True):
        yield


__all__ = ["SERVICE_TYPE_VARIABLE", "as_restricted_worker", "forbidden_credential_variables"]
