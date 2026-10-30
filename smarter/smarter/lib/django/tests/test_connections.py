"""Test close_thread_connections()."""

import threading
from unittest.mock import MagicMock, patch

from django.db import connection

from smarter.lib.django.connections import close_thread_connections
from smarter.lib.unittest.base_classes import SmarterTestBase


def in_thread(work):
    """Run ``work`` in a new thread, as an executor would, and return its result."""
    result = {}

    def run():
        result["value"] = work()

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()
    return result["value"]


class TestCloseThreadConnections(SmarterTestBase):
    """Test that a thread's open connections are closed, except one inside a transaction."""

    def test_closes_the_threads_connection(self):
        """A connection that a thread opened is closed, and the thread reconnects on its next query."""

        def work():
            connection.ensure_connection()
            opened = connection.connection is not None
            close_thread_connections()
            closed = connection.connection is None
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                reconnected = cursor.fetchone() == (1,)
            close_thread_connections()
            return opened, closed, reconnected

        self.assertEqual(in_thread(work), (True, True, True))

    def test_leaves_other_threads_alone(self):
        """Closing in a worker thread leaves this thread's connection open."""
        connection.ensure_connection()
        in_thread(close_thread_connections)
        self.assertIsNotNone(connection.connection)

    def test_skips_a_connection_inside_a_transaction(self):
        """A connection in an atomic block is left open, and one outside is closed."""
        in_transaction = MagicMock(in_atomic_block=True)
        idle = MagicMock(in_atomic_block=False)
        with patch("smarter.lib.django.connections.connections") as connections:
            connections.all.return_value = [in_transaction, idle]
            close_thread_connections()
        connections.all.assert_called_once_with(initialized_only=True)
        in_transaction.close.assert_not_called()
        idle.close.assert_called_once_with()
