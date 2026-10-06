"""Smarter unit test helpers."""

import sys


def running_unit_tests() -> bool:
    """
    Whether the process is the Django test runner, i.e. ``manage.py test``.

    Code that reaches real infrastructure, e.g. a cloud provider or an LLM provider, checks it to
    refuse to run in the unit tests, because the Smarter containers' credentials are real.
    """
    return "test" in sys.argv


__all__ = ["running_unit_tests"]
