"""Test :mod:`smarter.apps.llmtool.runner.http`: a safe HTTP request, through the tool runner."""

from unittest import mock

from smarter.apps.llmtool.plugin import safe_http
from smarter.apps.llmtool.plugin.tests.base_classes import (
    SAFE_HTTP_DNS_PATCH,
    FakeWebHost,
    mock_web_host,
    resolves_to,
)
from smarter.apps.llmtool.runner import ToolCall, ToolCallResult, executor_for
from smarter.apps.llmtool.runner.http import (
    HTTP_TOOL_CALL_KIND,
    HttpToolCall,
    execute_http_call,
    fetch_with_runner,
    value_to_response,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

URL = "https://api.example.com/search"
API_KEY = "test-http-api-key-value"


class TestHttpToolCall(SmarterTestBase):
    """Test the http kind of tool call, its executor, and fetch_with_runner()."""

    def test_call_travels_as_json_without_showing_its_credential(self):
        """Test that a request round-trips through JSON, and keeps its headers out of repr()."""
        call = HttpToolCall(
            url=URL,
            method="POST",
            headers={"X-Subscription-Token": API_KEY},
            params={"q": "a"},
            json_body={"b": [1]},
            accept_status=(200, 403),
            require_https=False,
        )
        self.assertEqual(call.kind, HTTP_TOOL_CALL_KIND)
        self.assertEqual(HttpToolCall.model_validate_json(call.model_dump_json()), call)
        self.assertNotIn(API_KEY, repr(call))

    def test_http_kind_is_registered(self):
        """Test that the tool runner finds this executor for the http kind."""
        self.assertIs(executor_for(HTTP_TOOL_CALL_KIND), execute_http_call)

    def test_fetch_with_runner_returns_what_fetch_returns(self):
        """Test that the response comes back whole, a binary body included, through the runner's JSON."""
        body = b"\x00\xffbinary\n"
        host = FakeWebHost()
        host.add("https://api.example.com/old", status_code=301, headers={"Location": "/search"})
        host.add(URL, body, headers={"Content-Type": "application/octet-stream; charset=utf-8"})
        with mock_web_host(host):
            response = fetch_with_runner("https://api.example.com/old", headers={"Accept": "a/b"}, params={"q": "a"})
        self.assertEqual(response.content, body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.url, URL)
        self.assertEqual(response.redirects, ["https://api.example.com/old"])
        self.assertEqual(response.content_type, "application/octet-stream")
        self.assertEqual(host.calls[0]["headers"]["Accept"], "a/b")
        self.assertEqual(host.calls[0]["params"], {"q": "a"})

    def test_fetch_with_runner_raises_as_fetch_does(self):
        """Test that an error status, and a refused url, raise SafeHttpError, with the status when there was one."""
        host = FakeWebHost()
        host.add(URL, b"", status_code=403)
        with mock_web_host(host):
            with self.assertRaises(safe_http.SafeHttpError) as context:
                fetch_with_runner(URL)
        self.assertEqual(context.exception.status_code, 403)
        with mock_web_host() as host, mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=resolves_to("10.0.0.5")):
            with self.assertRaises(safe_http.SafeHttpError) as context:
                fetch_with_runner("https://internal.example/")
        self.assertIsNone(context.exception.status_code)
        self.assertEqual(host.requested, [])

    def test_fetch_with_runner_goes_through_the_runner(self):
        """Test that fetch_with_runner() hands the runner an HttpToolCall with fetch's arguments."""
        runner = mock.MagicMock()
        runner.run.return_value = ToolCallResult(value={"url": URL, "headers": {}, "content": ""}, status_code=200)
        with mock.patch("smarter.apps.llmtool.runner.http.get_tool_runner", return_value=runner):
            fetch_with_runner(URL, method="HEAD", headers={"X-Subscription-Token": API_KEY}, timeout=3)
        call = runner.run.call_args.args[0]
        self.assertIsInstance(call, HttpToolCall)
        self.assertEqual(call.method, "HEAD")
        self.assertEqual(call.headers["X-Subscription-Token"], API_KEY)
        self.assertEqual(call.timeout, 3)

    def test_execute_needs_an_http_call(self):
        """Test that the executor refuses another kind of call."""
        with self.assertRaises(TypeError):
            execute_http_call(ToolCall(kind="other"))

    def test_invalid_value(self):
        """Test that a result whose value isn't a response raises SafeHttpError."""
        with self.assertRaises(safe_http.SafeHttpError):
            value_to_response("not a response", 200)
