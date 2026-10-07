"""Test :mod:`smarter.apps.provider.receivers`.

See :class:`smarter.lib.unittest.receivers.ReceiversTestMixin`.
"""

from smarter.apps.provider import receivers
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.receivers import ReceiversTestMixin


class TestProviderReceivers(ReceiversTestMixin, SmarterTestBase):
    """Call each receiver of the provider app with mock arguments."""

    receivers_module = receivers
    # this one queries the database for the sender's model.
    skip = ("provider_model_save",)
