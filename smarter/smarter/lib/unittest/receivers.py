"""
A test mixin that calls each signal receiver of a module, as its signal would, with a mock for each argument that the receiver names.

Celery's ``Task.apply_async``, and each Celery task that the module imports, are mocked, so that no receiver queues a
task. A receiver that only logs is then covered, and one that reads an argument that its signal does not send fails.
"""

import inspect
from types import ModuleType
from typing import Callable, Iterator
from unittest.mock import MagicMock, patch

from smarter.lib.typing import SmarterDictType


class ReceiversTestMixin:
    """
    Call each receiver of ``receivers_module`` with mock arguments.

    Mix it into a test base class that provides the :class:`unittest.TestCase` assertions.
    """

    #: The module whose receivers are tested.
    receivers_module: ModuleType
    #: Receivers that the test does not call, e.g. those that write to the database.
    skip: tuple[str, ...] = ()

    def setUp(self) -> None:
        """Patch ``Task.apply_async``, and every Celery task in the receivers module, until the end of the test."""
        super().setUp()  # type: ignore[misc]
        # no receiver may queue a task, however it imports it.
        patcher = patch("celery.app.task.Task.apply_async")
        patcher.start()
        self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
        for name, obj in inspect.getmembers(self.receivers_module):
            if hasattr(obj, "delay") and hasattr(obj, "apply_async"):
                patcher = patch.object(self.receivers_module, name)
                patcher.start()
                self.addCleanup(patcher.stop)  # type: ignore[attr-defined]

    def receivers(self) -> Iterator[tuple[str, Callable]]:
        """
        Yield the name and function of each receiver defined in the module, whose first parameter is ``sender``.

        Receivers named in ``skip`` are left out.

        :returns: An iterator of ``(name, function)`` tuples.
        """
        for name, function in inspect.getmembers(self.receivers_module, inspect.isfunction):
            if function.__module__ != self.receivers_module.__name__ or name in self.skip:
                continue
            parameters = list(inspect.signature(function).parameters)
            if parameters and parameters[0] == "sender":
                yield name, function

    def mock_arguments(self, function: Callable) -> SmarterDictType:
        """
        Return a mock keyword argument for each named parameter of a receiver, except ``sender``.

        ``created`` is True; every other argument is a :class:`~unittest.mock.MagicMock`.

        :param function: The receiver.
        :returns: The keyword arguments.
        """
        arguments = {}
        for name, parameter in inspect.signature(function).parameters.items():
            if name == "sender" or parameter.kind in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL):
                continue
            if name == "created":
                arguments[name] = True
            else:
                arguments[name] = MagicMock()
        return arguments

    class Sender:
        """The sender of each signal: a class, as most signals' senders are."""

    sender = Sender

    def test_receivers(self):
        """Each receiver runs with mock arguments, and with ``created`` False when it takes it."""
        receivers = list(self.receivers())
        self.assertTrue(receivers)  # type: ignore[attr-defined]
        for name, function in receivers:
            with self.subTest(receiver=name):  # type: ignore[attr-defined]
                arguments = self.mock_arguments(function)
                function(sender=self.sender, **arguments)
                if "created" in arguments:
                    function(sender=self.sender, **{**arguments, "created": False})
