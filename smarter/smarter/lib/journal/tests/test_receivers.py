"""Test :mod:`smarter.lib.journal.receivers`.

See :class:`smarter.lib.unittest.receivers.ReceiversTestMixin`.
"""

from smarter.lib.journal import receivers
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.receivers import ReceiversTestMixin


class TestJournalReceivers(ReceiversTestMixin, SmarterTestBase):
    """Call each receiver of the journal with mock arguments."""

    receivers_module = receivers
