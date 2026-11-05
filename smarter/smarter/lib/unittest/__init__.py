"""Smarter unit test helpers."""

import sys


def running_unit_tests() -> bool:
    """
    Return whether the process is the Django test runner, i.e. ``manage.py test``.

    Code that reaches real infrastructure, e.g. a cloud provider or an LLM provider, checks it to
    refuse to run in the unit tests, because the Smarter containers' credentials are real.

    :returns: True if ``test`` is one of the command line arguments.
    """
    running = "test" in sys.argv
    return running


__all__ = ["running_unit_tests"]
