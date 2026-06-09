"""Signals for connection app."""

from django.dispatch import Signal

sql_connection_attempted = Signal()
"""
Signal sent when a SQL connection is attempted.

Arguments:
    connection: The SQL connection instance being attempted.

Example::

    sql_connection_attempted.send(sender=self.__class__, connection=self)
"""

sql_connection_success = Signal()
"""
Signal sent when a SQL connection is successful.

Arguments:
    connection: The SQL connection instance that was successful.

Example::

    sql_connection_success.send(sender=self.__class__, connection=self)
"""

sql_connection_failed = Signal()
"""
Signal sent when a SQL connection fails.

Arguments:
    connection: The SQL connection instance that failed.
    error: The error message associated with the failure.

Example::

    sql_connection_failed.send(sender=self.__class__, connection=self, error=msg)
"""
sql_connection_query_attempted = Signal()
"""
Signal sent when a SQL connection query is attempted.

Arguments:
    connection: The SQL connection instance being queried.
    sql: The SQL query being executed.
    limit: The limit applied to the query (if any).

Example::

    sql_connection_query_attempted.send(sender=self.__class__, connection=self, sql=sql, limit=limit)
"""

sql_connection_query_success = Signal()
"""
Signal sent when a SQL connection query is successful.

Arguments:
    connection: The SQL connection instance that was queried.
    sql: The SQL query that was executed.
    limit: The limit applied to the query (if any).

Example::

    sql_connection_query_success.send(sender=self.__class__, connection=self, sql=sql, limit=limit)
"""

sql_connection_query_failed = Signal()
"""
Signal sent when a SQL connection query fails.

Arguments:
    connection: The SQL connection instance that was queried.
    sql: The SQL query that was executed.
    limit: The limit applied to the query (if any).
    error: The error message associated with the failure.

Example::

    sql_connection_query_failed.send(
        sender=self.__class__, connection=self, sql=sql, limit=limit, error=str(e)
    )

"""

sql_connection_validated = Signal()
"""
Signal sent when a SQL connection is validated.

Arguments:
    connection: The SQL connection instance that was validated.

Example::

    sql_connection_validated.send(sender=self.__class__, connection=self)
"""

api_connection_attempted = Signal()
"""
Signal sent when an API connection is attempted.

Arguments:
    connection: The API connection instance being attempted.

Example::

    api_connection_attempted.send(sender=self.__class__, connection=self)
"""

api_connection_success = Signal()
"""
Signal sent when an API connection is successful.

Arguments:
    connection: The API connection instance that was successful.

Example::

    api_connection_success.send(sender=self.__class__, connection=self)
"""

api_connection_failed = Signal()
"""
Signal sent when an API connection fails.

Arguments:
    connection: The API connection instance that failed.

Example::

    api_connection_failed.send(sender=self.__class__, connection=self, response=response, error=None)
"""

api_connection_query_attempted = Signal()
"""
Signal sent when an API connection query is attempted.

Arguments:
    connection: The API connection instance being queried.

Example::

    api_connection_query_attempted.send(sender=self.__class__, connection=self)
"""

api_connection_query_success = Signal()
"""
Signal sent when an API connection query is successful.

Arguments:
    connection: The API connection instance that was queried.
    response: The response returned from the API query.

Example::

    api_connection_query_success.send(sender=self.__class__, connection=self, response=response)
"""

api_connection_query_failed = Signal()
"""
Signal sent when an API connection query fails.

Arguments:
    connection: The API connection instance that was queried.
    response: The response returned from the API query.
    error: The error message associated with the failure.

Example::

    api_connection_query_failed.send(sender=self.__class__, connection=self, response=response, error=e)
"""


broker_ready = Signal()
"""
Signal sent when a broker achieves a ready state.

Arguments:
    broker: The broker instance that is ready.

Example::

    broker_ready.send(sender=self.__class__, broker=self)
"""
