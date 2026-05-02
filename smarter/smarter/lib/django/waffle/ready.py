"""
is_database_ready() - Check if the database is ready by verifying the connection and the existence of the waffle_switch table.
"""

from django.core.exceptions import SynchronousOnlyOperation
from django.db import connections
from django.db.utils import OperationalError, ProgrammingError


# pylint: disable=C0115
class DbState:
    ready = False


db_state = DbState()


def is_database_ready(alias="default"):
    """
    Check if the database is ready by verifying the connection and
    the existence of the waffle_switch table.

    :param alias: The database alias to check.
    :return: True if the database is ready, False otherwise.
    """

    if db_state.ready:
        return True
    try:
        # Ensure the connection is usable. ie the DB server is up
        connection = connections[alias]
        connection.ensure_connection()
        # Check if the waffle_switch table exists
        if "waffle_switch" not in connection.introspection.table_names():
            return False
        db_state.ready = True
        return db_state.ready
    except (OperationalError, SynchronousOnlyOperation):
        # we'll get SynchronousOnlyOperation whenever an ASGI asynchronous
        # context tries to interact with the database. Main culprit is middleware.
        return False
    except ProgrammingError:
        return False
