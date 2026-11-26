"""
The execution of an ApiPlugin's request, from its resolved :class:`ApiToolCall`, and of a SqlPlugin's query, from its resolved :class:`SqlToolCall`.

:meth:`ApiConnection.execute_query <smarter.apps.connection.models.ApiConnection.execute_query>`
resolves each request in the app, into an :class:`ApiToolCall`: the full url, and the headers with the
connection's ``Authorization`` already added from its Smarter Secret. The tool runner
(:mod:`smarter.apps.llmtool.runner`) executes it with :func:`execute_api_call`, which reads no
database, so the same call can run in the app's process today, or in a worker without credentials
(ADR-038).

The request is made with :func:`smarter.apps.llmtool.plugin.safe_http.fetch`: plain http and any port
are permitted, but every url, the first and each redirect's, must resolve to public addresses only,
except loopback hosts in the local environment. A redirect to another origin drops the
``Authorization`` header.

:meth:`SqlConnection.execute_query <smarter.apps.connection.models.SqlConnection.execute_query>`
resolves each query into a :class:`SqlToolCall`: the database's settings, with its password decrypted,
the SSH tunnel's, if any, with its password and known host keys, and the final SQL. The tool runner
executes it with :func:`execute_sql_call`, which opens the tunnel, connects, runs the query and closes
both, without the app's database.
"""

from http import HTTPStatus
from typing import Final, Literal, Optional

from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError
from django.db.utils import ConnectionHandler
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from smarter.apps.llmtool.plugin.safe_http import DEFAULT_TIMEOUT, SafeHttpError, fetch
from smarter.apps.llmtool.runner import ToolCall, ToolCallResult
from smarter.lib import json
from smarter.lib.typing import SmarterDictType

from .ssh import LOOPBACK, SshTunnel, SshTunnelError

API_TOOL_CALL_KIND: Final = "api"
"""The ``kind`` of an ApiPlugin's call, which selects :func:`execute_api_call`."""

API_MAX_RESPONSE_BYTES = 10_000_000
"""The largest api response that :func:`execute_api_call` reads, in bytes."""

SUCCESS_STATUS_CODES = tuple(range(200, 300))
"""
The status codes that :func:`~smarter.apps.llmtool.plugin.safe_http.fetch` returns rather than raises.

Only 200 is a successful query. The others are answered, but report the query as failed.
"""


class ApiToolCall(ToolCall):
    """
    An ApiPlugin's request, resolved for execution.

    .. warning::

        ``headers`` holds the connection's credential. It is excluded from ``repr()``. Never log the
        call's ``model_dump()``.

    :ivar url: The full url: the connection's base url joined with the plugin's endpoint.
    :ivar method: The HTTP method, upper case.
    :ivar headers: The request headers, with the connection's ``Authorization``.
    :ivar params: The query string parameters.
    :ivar json_body: The JSON body, for POST, PUT and PATCH, or None.
    :ivar timeout: Seconds to wait for each request.
    :ivar limit: The number of items to keep from the response, or None for all of them.
    """

    kind: Literal["api"] = API_TOOL_CALL_KIND
    url: str
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict, repr=False)
    params: dict[str, JsonValue] = Field(default_factory=dict)
    json_body: JsonValue = None
    timeout: float = DEFAULT_TIMEOUT
    limit: Optional[int] = None


def limit_response(response_data: JsonValue, limit: Optional[int]) -> JsonValue:
    """
    Limit an api's JSON response to ``limit`` items.

    A list keeps its first ``limit`` items. A dict keeps every key, and each of its values that is
    a list keeps its first ``limit`` items. Anything else, or no limit, is returned as it is.

    :param response_data: The parsed response.
    :param limit: The number of items to keep, or None or 0 for all of them.
    :returns: The limited response.
    """
    if not limit:
        return response_data
    if isinstance(response_data, list):
        return response_data[:limit]
    if not isinstance(response_data, dict):
        return response_data
    limited: dict[str, JsonValue] = {}
    for key, value in response_data.items():
        if isinstance(value, list):
            limited[key] = value[:limit]
        else:
            limited[key] = value
    return limited


def execute_api_call(call: ToolCall) -> ToolCallResult:
    """
    Execute a resolved ApiPlugin request.

    :param call: The call, an :class:`ApiToolCall`.
    :returns: The api's JSON, limited, with status 200; or a result with a ``failure``: when the url
        is refused or can't be reached (no ``status_code``), when the api answers with an error
        status, or with a 2xx other than 200, or when its answer isn't JSON (with its
        ``status_code``).
    :raises TypeError: If the call isn't an :class:`ApiToolCall`.
    """
    if not isinstance(call, ApiToolCall):
        raise TypeError(f"execute_api_call() needs an ApiToolCall, not a {type(call).__name__}.")
    try:
        response = fetch(
            call.url,
            method=call.method,
            headers=call.headers,
            params=call.params,
            json_body=call.json_body,
            timeout=call.timeout,
            max_bytes=API_MAX_RESPONSE_BYTES,
            accept_status=SUCCESS_STATUS_CODES,
            require_https=False,
            permit_local_loopback=True,
        )
    except SafeHttpError as e:
        return ToolCallResult(failure=str(e), status_code=e.status_code)
    if response.status_code != HTTPStatus.OK:
        return ToolCallResult(failure=f"the api answered HTTP {response.status_code}", status_code=response.status_code)
    try:
        response_data = response.json()
    except ValueError:
        return ToolCallResult(failure="the api's answer is not JSON", status_code=response.status_code)
    limited = limit_response(response_data, call.limit)
    result = ToolCallResult(value=limited, status_code=response.status_code)
    return result


SQL_TOOL_CALL_KIND: Final = "sql"
"""The ``kind`` of a SqlPlugin's query, which selects :func:`execute_sql_call`."""


class SshTunnelSettings(BaseModel):
    """
    The SSH tunnel of a SqlConnection whose ``authenticationMethod`` is ``tcpip_ssh``, resolved.

    See :mod:`smarter.apps.connection.ssh`.

    :ivar host: The SSH server.
    :ivar port: Its port.
    :ivar username: The SSH login.
    :ivar password: Its password, decrypted. Excluded from ``repr()``.
    :ivar known_hosts: The SSH server's host keys, in ``known_hosts`` format.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str
    port: int = 22
    username: Optional[str] = None
    password: Optional[str] = Field(default=None, repr=False)
    known_hosts: Optional[str] = None


class SqlToolCall(ToolCall):
    """
    A SqlPlugin's query, resolved for execution.

    .. warning::

        ``password``, and the SSH tunnel's, hold credentials. They are excluded from ``repr()``.
        Never log the call's ``model_dump()``.

    :ivar engine: The Django database backend, e.g. ``django.db.backends.mysql``.
    :ivar database: The database's name.
    :ivar username: The database login.
    :ivar password: Its password, decrypted.
    :ivar host: The database's host. With an SSH tunnel, as the SSH server reaches it.
    :ivar port: The database's port.
    :ivar options: The driver's options: timeouts, TLS, LDAP.
    :ivar ssh: The SSH tunnel, or None.
    :ivar sql: The final SQL, with its limit.
    :ivar timeout: Seconds to wait for the SSH server.
    """

    kind: Literal["sql"] = SQL_TOOL_CALL_KIND
    engine: str
    database: str
    username: Optional[str] = None
    password: Optional[str] = Field(default=None, repr=False)
    host: str
    port: int
    options: dict[str, JsonValue] = Field(default_factory=dict)
    ssh: Optional[SshTunnelSettings] = None
    sql: str
    timeout: float = 30


def database_settings(call: SqlToolCall, host: str, port: int) -> SmarterDictType:
    """
    Return Django's settings for a call's database, at a host and port.

    :param call: The call.
    :param host: The host to connect to: the database's, or the SSH tunnel's loopback.
    :param port: Its port.
    :returns: Settings for :class:`django.db.utils.ConnectionHandler`.
    """
    settings: SmarterDictType = {
        "ENGINE": call.engine,
        "NAME": call.database,
        "USER": call.username,
        "PASSWORD": call.password,
        "HOST": host,
        "PORT": str(port),
        "OPTIONS": call.options,
    }
    return settings


def rows_as_json(cursor) -> str:
    """
    Return a query's rows as a JSON list of objects, one per row, keyed by column.

    :param cursor: The cursor, after the query ran.
    :returns: The JSON.
    """
    columns = [column[0] for column in cursor.description or []]
    rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append(dict(zip(columns, row)))
    text = json.dumps(result)
    return text


def query_database(call: SqlToolCall, host: str, port: int) -> ToolCallResult:
    """
    Connect to a call's database at a host and port, run its query, and disconnect.

    :param call: The call.
    :param host: The host to connect to.
    :param port: Its port.
    :returns: The rows as JSON; a result with ``is_error`` and the database's message when the query
        fails; or a result with a ``failure`` when the database can't be reached or refuses the login.
    """
    connection_handler = ConnectionHandler({"default": database_settings(call, host, port)})
    database = connection_handler["default"]
    try:
        try:
            database.ensure_connection()
        except (DatabaseError, ImproperlyConfigured) as e:
            return ToolCallResult(failure=f"could not connect to the database: {e}")
        try:
            with database.cursor() as cursor:
                cursor.execute(call.sql)
                rows = rows_as_json(cursor)
        except (DatabaseError, ImproperlyConfigured) as e:
            return ToolCallResult(value=str(e), is_error=True)
    finally:
        database.close()
    result = ToolCallResult(value=rows)
    return result


def execute_sql_call(call: ToolCall) -> ToolCallResult:
    """
    Execute a resolved SqlPlugin query, through its SSH tunnel if it has one.

    :param call: The call, a :class:`SqlToolCall`.
    :returns: The rows as JSON, a database error with ``is_error``, or a ``failure`` when the SSH
        tunnel can't be opened or the database can't be reached.
    :raises TypeError: If the call isn't a :class:`SqlToolCall`.
    """
    if not isinstance(call, SqlToolCall):
        raise TypeError(f"execute_sql_call() needs a SqlToolCall, not a {type(call).__name__}.")
    if call.ssh is None:
        return query_database(call, call.host, call.port)
    tunnel = SshTunnel(
        ssh_host=call.ssh.host,
        ssh_port=call.ssh.port,
        username=call.ssh.username,
        password=call.ssh.password,
        known_hosts=call.ssh.known_hosts,
        remote_host=call.host,
        remote_port=call.port,
        timeout=call.timeout,
    )
    try:
        with tunnel:
            result = query_database(call, LOOPBACK, tunnel.local_port)
    except SshTunnelError as e:
        return ToolCallResult(failure=f"could not open the SSH tunnel: {e}")
    return result


__all__ = [
    "API_MAX_RESPONSE_BYTES",
    "API_TOOL_CALL_KIND",
    "SQL_TOOL_CALL_KIND",
    "SUCCESS_STATUS_CODES",
    "ApiToolCall",
    "SqlToolCall",
    "SshTunnelSettings",
    "database_settings",
    "execute_api_call",
    "execute_sql_call",
    "limit_response",
    "query_database",
    "rows_as_json",
]
