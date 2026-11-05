"""Test :mod:`smarter.lib.journal.receivers`.

See :class:`smarter.lib.unittest.receivers.ReceiversTestMixin`.
"""

from unittest.mock import patch

from smarter.lib.journal import receivers
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.receivers import ReceiversTestMixin


class TestJournalReceivers(ReceiversTestMixin, SmarterTestBase):
    """Call each receiver of the journal with mock arguments."""

    receivers_module = receivers

    def test_failed_entry_never_logs_the_documents(self):
        """The request and response documents hold credentials, so they are not logged."""
        with patch.object(receivers, "error_logger") as error_logger:
            receivers.journal_entry_failed_receiver(
                sender=None,
                user=None,
                thing="Secret",
                command="apply",
                status=500,
                request={"META": {"HTTP_AUTHORIZATION": "Token not-a-real-key"}},
                response={"data": "not-a-real-secret-value"},
                error=ValueError("boom"),
            )
        logged = str(error_logger.error.call_args_list)
        self.assertNotIn("not-a-real", logged)
        self.assertIn("could not create journal entry", logged)
