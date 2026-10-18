"""Signals of SqlPlugin tool calls."""

from django.dispatch import Signal

sql_plugin_request_started = Signal()
"""
Signal sent when a SqlPlugin tool call begins: a SQL query.

Arguments:
    plugin: The SqlPlugin instance.
    function_args: The tool call's arguments, as the LLM sent them.

Example::

    sql_plugin_request_started.send(sender=self.__class__, plugin=self, function_args=function_args)
"""

sql_plugin_authenticated = Signal()
"""
Signal sent when the plugin's SqlConnection connects to its database, which includes authenticating to it.

Not sent when the result is served from the cache.

Arguments:
    plugin: The SqlPlugin instance.
    connection: The name of the SqlConnection.

Example::

    sql_plugin_authenticated.send(sender=self.__class__, plugin=self, connection="stackademy")
"""

sql_plugin_authentication_failed = Signal()
"""
Signal sent when the plugin's SqlConnection cannot connect to its database: its credentials are rejected, or the database, or its SSH tunnel, cannot be reached.

The database drivers do not tell these apart.

Arguments:
    plugin: The SqlPlugin instance.
    connection: The name of the SqlConnection.
    error: What went wrong.

Example::

    sql_plugin_authentication_failed.send(sender=self.__class__, plugin=self, connection="stackademy", error="could not connect to the database")
"""

sql_plugin_responded = Signal()
"""
Signal sent when a SqlPlugin tool call returns its response to the LLM.

Arguments:
    plugin: The SqlPlugin instance.
    response: The query result, as a JSON string, or an empty string if the query returned no rows.
    cached: True if the result was served from the cache.
    sql: The SQL query, with the arguments interpolated.

Example::

    sql_plugin_responded.send(sender=self.__class__, plugin=self, response='[{"course_code": "CS101"}]', cached=False, sql="SELECT ...;")
"""

sql_plugin_failed = Signal()
"""
Signal sent when a SqlPlugin tool call fails, whether it raises or returns an empty response to the LLM.

Arguments:
    plugin: The SqlPlugin instance.
    error: What went wrong. It never contains credentials.

Example::

    sql_plugin_failed.send(sender=self.__class__, plugin=self, error="SQL query failed")
"""

sql_plugin_request_completed = Signal()
"""
Signal sent when a SqlPlugin tool call ends, successfully or not.

It is always the last signal of the call.

Arguments:
    plugin: The SqlPlugin instance.
    success: False if sql_plugin_failed was sent.
    duration: The seconds that the tool call took.

Example::

    sql_plugin_request_completed.send(sender=self.__class__, plugin=self, success=True, duration=0.42)
"""
