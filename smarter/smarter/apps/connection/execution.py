"""
The execution of an ApiPlugin's request, from its resolved :class:`ApiToolCall`.

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
"""

from http import HTTPStatus
from typing import Final, Literal, Optional

from pydantic import Field, JsonValue

from smarter.apps.llmtool.plugin.safe_http import DEFAULT_TIMEOUT, SafeHttpError, fetch
from smarter.apps.llmtool.runner import ToolCall, ToolCallResult

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


__all__ = [
    "API_MAX_RESPONSE_BYTES",
    "API_TOOL_CALL_KIND",
    "SUCCESS_STATUS_CODES",
    "ApiToolCall",
    "execute_api_call",
    "limit_response",
]
