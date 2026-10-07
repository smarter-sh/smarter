"""
The base class of the infrastructure app's tests.

Every test runs against an :class:`~smarter.apps.infrastructure.providers.memory.InMemoryProvider`,
installed with :func:`~smarter.apps.infrastructure.providers.configure_provider`, so that nothing
reaches real infrastructure. The ledger rows that a test's signals create are deleted afterwards.
"""

from typing import Any

from django.dispatch import Signal

from smarter.apps.infrastructure.models import InfrastructureResource
from smarter.apps.infrastructure.providers import configure_provider
from smarter.apps.infrastructure.providers.memory import InMemoryProvider
from smarter.apps.infrastructure.services import configure_email, configure_kubernetes
from smarter.lib.unittest.base_classes import SmarterTestBase


class InfrastructureTestBase(SmarterTestBase):
    """Install an in-memory provider, and clean up the ledger."""

    def setUp(self):
        super().setUp()
        last_id = InfrastructureResource.objects.order_by("-id").values_list("id", flat=True).first() or 0
        self.addCleanup(lambda: InfrastructureResource.objects.filter(id__gt=last_id).delete())
        self.provider = InMemoryProvider()
        configure_provider(lambda: self.provider)
        self.addCleanup(configure_provider, None)
        self.addCleanup(configure_kubernetes, None)
        self.addCleanup(configure_email, None)

    def capture(self, *signals: Signal) -> list[tuple[Signal, dict[str, Any]]]:
        """Record the signals that are sent, with their arguments, until the test ends."""
        events: list[tuple[Signal, dict[str, Any]]] = []

        def handler(sender, **kwargs):
            events.append((kwargs.pop("signal"), {"sender": sender, **kwargs}))

        for signal in signals:
            signal.connect(handler, weak=False)
            self.addCleanup(signal.disconnect, handler)
        return events

    @staticmethod
    def sent(events: list[tuple[Signal, dict[str, Any]]], signal: Signal) -> list[dict[str, Any]]:
        """The arguments of each time that a signal was sent."""
        return [kwargs for sent_signal, kwargs in events if sent_signal is signal]
