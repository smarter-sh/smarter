"""Test :mod:`smarter.apps.connection.execution`: the execution of a resolved ApiPlugin request."""

from unittest import mock

from smarter.apps.connection.execution import (
    API_TOOL_CALL_KIND,
    ApiToolCall,
    execute_api_call,
    limit_response,
)
from smarter.apps.llmtool.plugin.tests.base_classes import (
    SAFE_HTTP_DNS_PATCH,
    SAFE_HTTP_SETTINGS_PATCH,
    FakeWebHost,
    mock_web_host,
    resolves_to,
)
from smarter.apps.llmtool.runner import ToolCall, executor_for
from smarter.common.const import SmarterEnvironments
from smarter.lib.unittest.base_classes import SmarterTestBase

API_URL = "https://api.example.com/v1/items"
SECRET_HEADER = "Bearer test-api-key-value"


class TestApiExecution(SmarterTestBase):
    """Test the execution of a resolved ApiPlugin request, without the database."""

    def call(self, url: str = API_URL, **fields) -> ApiToolCall:
        """Return a resolved request."""
        call = ApiToolCall(url=url, headers={"Authorization": SECRET_HEADER}, **fields)
        return call

    def test_call_travels_as_json_without_showing_its_credential(self):
        """Test that a resolved request survives JSON, and keeps its Authorization header out of repr()."""
        call = self.call(method="POST", params={"q": "a"}, json_body={"page": 2}, limit=5)
        self.assertEqual(call.kind, API_TOOL_CALL_KIND)
        self.assertEqual(ApiToolCall.model_validate_json(call.model_dump_json()), call)
        self.assertNotIn(SECRET_HEADER, repr(call))

    def test_api_kind_is_registered(self):
        """Test that the tool runner finds this executor for the api kind."""
        self.assertIs(executor_for(API_TOOL_CALL_KIND), execute_api_call)

    def test_success(self):
        """Test that the api's JSON is returned, limited, with its status, and the request is sent as resolved."""
        host = FakeWebHost()
        host.add_json(API_URL, [1, 2, 3, 4])
        with mock_web_host(host):
            result = execute_api_call(self.call(method="POST", params={"q": "a"}, json_body={"page": 2}, limit=2))
        self.assertEqual(result.value, [1, 2])
        self.assertEqual(result.status_code, 200)
        self.assertIsNone(result.failure)
        sent = host.calls[0]
        self.assertEqual(sent["method"], "POST")
        self.assertEqual(sent["headers"]["Authorization"], SECRET_HEADER)
        self.assertEqual(sent["params"], {"q": "a"})
        self.assertEqual(sent["json"], {"page": 2})

    def test_error_status(self):
        """Test that an error status is a failure, with the status, so that a rejected credential can be told apart."""
        host = FakeWebHost()
        host.add(API_URL, b"", status_code=401)
        with mock_web_host(host):
            result = execute_api_call(self.call())
        self.assertIsNotNone(result.failure)
        self.assertEqual(result.status_code, 401)

    def test_other_success_status(self):
        """Test that a 2xx other than 200 is a failure, with its status."""
        host = FakeWebHost()
        host.add(API_URL, b"", status_code=204)
        with mock_web_host(host):
            result = execute_api_call(self.call())
        self.assertIsNotNone(result.failure)
        self.assertEqual(result.status_code, 204)

    def test_not_json(self):
        """Test that an answer that isn't JSON is a failure, with status 200."""
        host = FakeWebHost()
        host.add(API_URL, b"<html>not json</html>")
        with mock_web_host(host):
            result = execute_api_call(self.call())
        self.assertIn("not JSON", result.failure or "")
        self.assertEqual(result.status_code, 200)

    def test_refused_url_has_no_status(self):
        """Test that a url that isn't public is refused, in a deployed environment, before any request, and has no status."""
        with (
            mock.patch(SAFE_HTTP_SETTINGS_PATCH) as settings,
            mock_web_host() as host,
            # after mock_web_host(), which resolves every host to a public address.
            mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=resolves_to("169.254.169.254")),
        ):
            settings.environment = SmarterEnvironments.PROD
            result = execute_api_call(self.call("http://metadata.internal/latest/"))
        self.assertIsNotNone(result.failure)
        self.assertIsNone(result.status_code)
        self.assertEqual(host.requested, [])

    def test_needs_an_api_call(self):
        """Test that the executor refuses another kind of call."""
        with self.assertRaises(TypeError):
            execute_api_call(ToolCall(kind="other"))

    def test_limit_response(self):
        """Test that a list keeps its first items, a dict's lists do, and anything else is unchanged."""
        self.assertEqual(limit_response([1, 2, 3], 2), [1, 2])
        self.assertEqual(limit_response({"a": [1, 2, 3], "b": "x"}, 1), {"a": [1], "b": "x"})
        self.assertEqual(limit_response("text", 1), "text")
        self.assertEqual(limit_response([1, 2, 3], None), [1, 2, 3])
        self.assertEqual(limit_response([1, 2, 3], 0), [1, 2, 3])
