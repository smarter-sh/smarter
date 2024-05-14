# pylint: disable=wrong-import-position
"""Test User."""

# python stuff
import unittest

from django.db import connections
from django.db.utils import OperationalError


class TestMySQL(unittest.TestCase):
    """Test Account model"""

    def test_mysql_is_available(self):
        """Test that MySQL is reachable."""
        db_conn = connections["default"]
        try:
            db_conn.cursor()
        except OperationalError:
            self.fail("MySQL is unavailable")
        finally:
            db_conn.close()
