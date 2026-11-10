"""Smarter unit test helpers."""

import sys
from typing import Protocol


def running_unit_tests() -> bool:
    """
    Return whether the process is the Django test runner, i.e. ``manage.py test``.

    Code that reaches real infrastructure, e.g. a cloud provider or an LLM provider, checks it to
    refuse to run in the unit tests, because the Smarter containers' credentials are real.

    :returns: True if ``test`` is one of the command line arguments.
    """
    running = "test" in sys.argv
    return running


class ReverseNamesClass(Protocol):
    """
    An app's ``<App>ReverseNames`` class, e.g. ``ProviderReverseNames``, which the test mixins reverse urls by.

    The class itself is used, not an instance: its ``namespace`` and its url names are class
    attributes.
    """

    @property
    def namespace(self) -> str:
        """The app's url namespace."""
        raise NotImplementedError


__all__ = ["ReverseNamesClass", "running_unit_tests"]
