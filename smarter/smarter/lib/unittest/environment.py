"""
The process environment that a test needs to build ``Settings`` as a restricted worker's.

The tests run in ``smarter-api``, whose environment holds the platform's credentials, from ``.env``. A test
that builds ``Settings(database_unavailable=True)``, to stand in for the tool worker or the Extension worker,
would be refused by :meth:`~smarter.common.conf.settings.Settings.check_restricted_worker_credentials`: a real
restricted worker is never given those credentials. :func:`without_credentials` takes them out of the
environment for the duration of a ``with`` block, as a deployment never put them in.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

from smarter.common.conf import Settings
from smarter.common.conf.credentials import (
    environment_variables,
    is_credential,
    restricted_workers_may_hold,
)


def forbidden_credential_variables() -> list[str]:
    """
    Return the environment variables of every credential that the restricted workers must not hold.

    :returns: The variables' names, e.g. ``SMARTER_APP_PROVIDER_OPENAI_API_KEY``.
    """
    retval: list[str] = []
    for name, field in Settings.model_fields.items():
        if not is_credential(field):
            continue
        if restricted_workers_may_hold(field):
            continue
        retval.extend(environment_variables(name, field))
    return retval


@contextmanager
def without_credentials() -> Iterator[None]:
    """
    Remove from the environment, inside the ``with`` block, every credential that a restricted worker must not hold.

    The rest of the environment, and the Redis password that the restricted workers may hold, are left alone.
    """
    remaining = dict(os.environ)
    for variable in forbidden_credential_variables():
        remaining.pop(variable, None)
    with patch.dict(os.environ, remaining, clear=True):
        yield


__all__ = ["forbidden_credential_variables", "without_credentials"]
