# pylint: disable=wrong-import-position
"""Test User."""

from django.db import connections
from django.db.utils import OperationalError

from smarter.lib.unittest.base_classes import SmarterTestBase


class TestMariaDB(SmarterTestBase):
    """Test Account model."""

    def test_mysql_is_available(self):
        """Test that MariaDB is reachable."""
        db_conn = connections["default"]
        try:
            db_conn.cursor()
        except OperationalError:
            self.fail("MariaDB is unavailable")
        finally:
            db_conn.close()
