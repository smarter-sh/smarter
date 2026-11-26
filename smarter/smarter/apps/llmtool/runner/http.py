"""
A safe HTTP request, executed by the tool runner: the ``http`` kind of tool call.

Several tools make one request to a url with :func:`smarter.apps.llmtool.plugin.safe_http.fetch`, often
with an api key in a header: the WebsearchPlugin's search apis (Brave, Tavily), and the
ImageSearchPlugin's Brave image search and its checks of each image's url. :func:`fetch_with_runner`
takes the place of ``fetch`` for them. It resolves the request into an :class:`HttpToolCall`, which
the tool runner executes with :func:`execute_http_call`, and turns the result back into a
:class:`~smarter.apps.llmtool.plugin.safe_http.SafeResponse`, or raises
:class:`~smarter.apps.llmtool.plugin.safe_http.SafeHttpError`, as ``fetch`` does. The caller is
unchanged, and the request can run in a worker without credentials (ADR-038).

``fetch``'s ``redirect_policy``, a function, can't travel with a call, so a request that needs one,
such as the WebsearchPlugin's fetch of a page, isn't an ``http`` call.

Nothing here logs or reads the database: the ImageSearchPlugin checks image urls in worker
threads, where either would open a database connection per thread.
"""

import base64
from typing import Final, Literal, Optional

from pydantic import Field, JsonValue

from smarter.apps.llmtool.plugin import safe_http
from smarter.lib.typing import SmarterDictType

from .models import ToolCall, ToolCallResult
from .runner import get_tool_runner

HTTP_TOOL_CALL_KIND: Final = "http"
"""The ``kind`` of a safe HTTP request, which selects :func:`execute_http_call`."""


class HttpToolCall(ToolCall):
    """
    A safe HTTP request, resolved for execution: the arguments of :func:`~smarter.apps.llmtool.plugin.safe_http.fetch`.

    .. warning::

        ``headers`` may hold an api key. It is excluded from ``repr()``. Never log the call's
        ``model_dump()``.
    """

    kind: Literal["http"] = HTTP_TOOL_CALL_KIND
    url: str
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict, repr=False)
    params: Optional[dict[str, JsonValue]] = None
    json_body: JsonValue = None
    timeout: float = safe_http.DEFAULT_TIMEOUT
    max_bytes: int = safe_http.DEFAULT_MAX_BYTES
    max_redirects: int = safe_http.DEFAULT_MAX_REDIRECTS
    accept_status: tuple[int, ...] = (200,)
    require_https: bool = True
    permit_local_loopback: bool = False


def response_to_value(response: safe_http.SafeResponse) -> SmarterDictType:
    """
    Return a response as JSON: its url, headers and redirects, and its body in base64, so that any bytes survive.

    :param response: The response.
    :returns: The JSON value of a :class:`~smarter.apps.llmtool.runner.models.ToolCallResult`.
    """
    content = base64.b64encode(response.content).decode("ascii")
    value: SmarterDictType = {
        "url": response.url,
        "headers": response.headers,
        "content": content,
        "redirects": response.redirects,
    }
    return value


def value_to_response(value: JsonValue, status_code: int) -> safe_http.SafeResponse:
    """
    Return the response that :func:`response_to_value` turned into JSON.

    :param value: The result's value.
    :param status_code: The result's status code.
    :returns: The response.
    :raises SafeHttpError: If the value isn't a response.
    """
    if not isinstance(value, dict):
        raise safe_http.SafeHttpError("the tool runner returned an invalid response.")
    headers = value.get("headers") or {}
    redirects = value.get("redirects") or []
    content = base64.b64decode(str(value.get("content") or ""))
    response = safe_http.SafeResponse(
        url=str(value.get("url") or ""),
        status_code=status_code,
        headers={str(name): str(header) for name, header in dict(headers).items()},  # type: ignore[arg-type]
        content=content,
        redirects=[str(redirect) for redirect in list(redirects)],  # type: ignore[arg-type]
    )
    return response


def execute_http_call(call: ToolCall) -> ToolCallResult:
    """
    Execute a resolved safe HTTP request.

    :param call: The call, an :class:`HttpToolCall`.
    :returns: The response, from :func:`response_to_value`, with its status code; or a result with a
        ``failure``, and the status code if the server answered, when ``fetch`` raises.
    :raises TypeError: If the call isn't an :class:`HttpToolCall`.
    """
    if not isinstance(call, HttpToolCall):
        raise TypeError(f"execute_http_call() needs an HttpToolCall, not a {type(call).__name__}.")
    try:
        # safe_http.fetch, rather than an imported fetch, so that a test that patches it, patches this.
        response = safe_http.fetch(
            call.url,
            method=call.method,
            headers=call.headers,
            params=call.params,
            json_body=call.json_body,
            timeout=call.timeout,
            max_bytes=call.max_bytes,
            max_redirects=call.max_redirects,
            accept_status=call.accept_status,
            require_https=call.require_https,
            permit_local_loopback=call.permit_local_loopback,
        )
    except safe_http.SafeHttpError as e:
        return ToolCallResult(failure=str(e), status_code=e.status_code)
    result = ToolCallResult(value=response_to_value(response), status_code=response.status_code)
    return result


# pylint: disable=too-many-arguments
def fetch_with_runner(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    params: Optional[SmarterDictType] = None,
    json_body: JsonValue = None,
    timeout: float = safe_http.DEFAULT_TIMEOUT,
    max_bytes: int = safe_http.DEFAULT_MAX_BYTES,
    max_redirects: int = safe_http.DEFAULT_MAX_REDIRECTS,
    accept_status: tuple[int, ...] = (200,),
    require_https: bool = True,
    permit_local_loopback: bool = False,
) -> safe_http.SafeResponse:
    """
    Make a safe HTTP request through the tool runner: :func:`~smarter.apps.llmtool.plugin.safe_http.fetch`, as an :class:`HttpToolCall`.

    Its arguments are ``fetch``'s, but for ``redirect_policy``, which can't travel with a call.

    :returns: The response.
    :raises SafeHttpError: As ``fetch`` does: if a url is not permitted, the request fails or times
        out, the response status is not accepted, or the response is too large.
    """
    call = HttpToolCall(
        url=url,
        method=method,
        headers=headers or {},
        params=params,
        json_body=json_body,
        timeout=timeout,
        max_bytes=max_bytes,
        max_redirects=max_redirects,
        accept_status=accept_status,
        require_https=require_https,
        permit_local_loopback=permit_local_loopback,
    )
    result = get_tool_runner().run(call)
    if result.failure is not None:
        raise safe_http.SafeHttpError(result.failure, status_code=result.status_code)
    status_code = result.status_code or 0
    response = value_to_response(result.value, status_code)
    return response


__all__ = [
    "HTTP_TOOL_CALL_KIND",
    "HttpToolCall",
    "execute_http_call",
    "fetch_with_runner",
    "response_to_value",
    "value_to_response",
]
