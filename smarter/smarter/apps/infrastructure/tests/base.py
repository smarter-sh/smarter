"""
The base class of the infrastructure app's tests.

Every test runs against an :class:`~smarter.apps.infrastructure.providers.memory.InMemoryProvider`,
installed with :func:`~smarter.apps.infrastructure.providers.configure_provider`, so that nothing
reaches real infrastructure. The ledger rows that a test's signals create are deleted afterwards.

Each test also runs without the developer's AWS profile: see :data:`AWS_PROFILE_VARIABLES`.
"""

import os
from unittest.mock import patch

from django.dispatch import Signal

from smarter.apps.infrastructure.models import InfrastructureResource
from smarter.apps.infrastructure.providers import configure_provider
from smarter.apps.infrastructure.providers.memory import InMemoryProvider
from smarter.apps.infrastructure.services import (
    configure_email,
    configure_kubernetes,
    configure_logs,
    configure_slack,
)
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

AWS_PROFILE_VARIABLES = ("AWS_PROFILE", "AWS_DEFAULT_PROFILE")
"""
The environment variables that name an AWS profile, which each test runs without.

A local platform's containers read the developer's .env, whose AWS profile is not configured inside them.
botocore resolves the profile even for a session or client built with explicit test credentials, and raised
``ProfileNotFound`` before the test ran. In CI, which has no profile, the same tests passed.
"""


class InfrastructureTestBase(SmarterTestBase):
    """Install an in-memory provider, clean up the ledger, and hide the developer's AWS profile."""

    def setUp(self):
        super().setUp()
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        for variable in AWS_PROFILE_VARIABLES:
            os.environ.pop(variable, None)
        last_id = InfrastructureResource.objects.order_by("-id").values_list("id", flat=True).first() or 0
        self.addCleanup(lambda: InfrastructureResource.objects.filter(id__gt=last_id).delete())
        self.provider = InMemoryProvider()
        configure_provider(lambda: self.provider)
        self.addCleanup(configure_provider, None)
        self.addCleanup(configure_kubernetes, None)
        self.addCleanup(configure_email, None)
        self.addCleanup(configure_slack, None)
        self.addCleanup(configure_logs, None)

    def capture(self, *signals: Signal) -> list[tuple[Signal, SmarterDictType]]:
        """Record the signals that are sent, with their arguments, until the test ends."""
        events: list[tuple[Signal, SmarterDictType]] = []

        def handler(sender, **kwargs):
            events.append((kwargs.pop("signal"), {"sender": sender, **kwargs}))

        for signal in signals:
            signal.connect(handler, weak=False)
            self.addCleanup(signal.disconnect, handler)
        return events

    @staticmethod
    def sent(events: list[tuple[Signal, SmarterDictType]], signal: Signal) -> list[SmarterDictType]:
        """The arguments of each time that a signal was sent."""
        return [kwargs for sent_signal, kwargs in events if sent_signal is signal]
