# pylint: disable=too-many-lines,protected-access
"""
Unit tests for :py:class:`smarter.apps.plugin.plugin.api.ApiPlugin`, and for.

:py:meth:`smarter.apps.connection.models.ApiConnection.execute_query`, which backs it.

.. note::

    HTTP requests are mocked, except for the tests that send real requests to the
    local Smarter test api, which are skipped if it is not reachable.
"""

from types import SimpleNamespace
from unittest import mock, skipUnless

import requests
from django.core.cache import cache

from smarter.apps.connection.models import ApiConnection, SqlConnection
from smarter.apps.plugin.manifest.models.api_plugin.const import (
    MANIFEST_KIND as API_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.models import PluginDataApi, PluginMeta
from smarter.apps.plugin.plugin.api import (
    MAX_API_RESULTS,
    ApiPlugin,
    SmarterApiPluginError,
)
from smarter.apps.plugin.serializers import PluginApiSerializer
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json

from .base_classes import (
    API_CONNECTION_NAME,
    API_CONNECTION_NAME_2,
    API_ENDPOINT,
    API_REQUEST_PATCH,
    LIVE_API_PROBE_URL,
    PluginTestBase,
    live_api_is_available,
    mock_response,
)

LIVE_API_AVAILABLE = live_api_is_available()


# pylint: disable=too-many-public-methods
class TestApiPlugin(PluginTestBase):
    """Test ApiPlugin and ApiConnection.execute_query(), using the shared ApiPlugin fixture."""

    sql_fixtures = False

    # =========================================================================
    # fixtures
    # =========================================================================
    def test_000_fixtures(self):
        """Test the class fixtures themselves, lest we get ahead of ourselves."""
        self.assertTrue(self.ready)
        self.assertIsInstance(self.api_connection, ApiConnection)
        self.assertIsInstance(self.api_connection_2, ApiConnection)
        self.assertIsInstance(self.api_plugin, ApiPlugin)
        self.assertTrue(self.api_plugin.ready)
        self.assertEqual(self.api_plugin_yaml["spec"]["apiData"]["endpoint"], API_ENDPOINT)
        self.assertEqual(self.api_connection.api_key.get_secret(), self.api_key)  # type: ignore[union-attr]

    # =========================================================================
    # ApiPlugin: class structure
    # =========================================================================
    def test_api_class_attributes(self):
        """Test the ApiPlugin class attributes."""
        self.assertIs(ApiPlugin.SAMPluginType, SAMApiPlugin)
        self.assertEqual(self.api_plugin.kind, API_MANIFEST_KIND)
        self.assertIs(self.api_plugin.plugin_data_class, PluginDataApi)
        self.assertIs(self.api_plugin.plugin_data_serializer_class, PluginApiSerializer)

    def test_api_has_no_apply(self):
        """Test that the leftover apply() stub has been removed."""
        self.assertFalse(hasattr(ApiPlugin, "apply"))

    def test_api_plugin_data_serializer(self):
        """Test the ApiPlugin data serializer."""
        serializer = self.load_api_plugin().plugin_data_serializer
        self.assertIsInstance(serializer, PluginApiSerializer)
        self.assertEqual(serializer.data["endpoint"], API_ENDPOINT)  # type: ignore[union-attr]

    def test_api_plugin_data(self):
        """Test the ApiPlugin data Django model."""
        plugin_data = self.load_api_plugin().plugin_data
        self.assertIsInstance(plugin_data, PluginDataApi)
        self.assertEqual(plugin_data.endpoint, API_ENDPOINT)  # type: ignore[union-attr]
        self.assertEqual(plugin_data.method, "GET")  # type: ignore[union-attr]
        self.assertEqual(plugin_data.limit, 10)  # type: ignore[union-attr]
        self.assertEqual(plugin_data.connection, self.api_connection)  # type: ignore[union-attr]
        self.assertIsNone(plugin_data.body)  # type: ignore[union-attr]

    def test_api_plugin_data_headers(self):
        """Test that the ApiPlugin headers are persisted as a list of name/value dicts."""
        headers = self.load_api_plugin().plugin_data.headers  # type: ignore[union-attr]
        self.assertIn({"name": "Accept", "value": "application/json"}, headers)
        self.assertEqual(len(headers), 3)

    def test_api_plugin_data_url_params(self):
        """Test that the ApiPlugin url params are persisted as a list of key/value dicts."""
        self.assertEqual(
            self.load_api_plugin().plugin_data.url_params, [{"key": "source", "value": "smarter"}]  # type: ignore[union-attr]
        )

    def test_api_plugin_data_url(self):
        """Test the full url of the ApiPlugin endpoint."""
        self.assertEqual(
            self.load_api_plugin().plugin_data.url,  # type: ignore[union-attr]
            "http://localhost:9357/api/v1/tests/unauthenticated/{kind}/",
        )

    def test_api_manifest_from_database(self):
        """Test that the manifest is reconstructed from the database when not provided."""
        plugin = self.load_api_plugin()
        self.assertIsNone(plugin._manifest)
        manifest = plugin.manifest
        self.assertIsInstance(manifest, SAMApiPlugin)
        self.assertEqual(manifest.spec.apiData.endpoint, API_ENDPOINT)  # type: ignore[union-attr]
        self.assertEqual(manifest.spec.connection, API_CONNECTION_NAME)  # type: ignore[union-attr]

    def test_api_manifest_not_ready(self):
        """Test that the manifest is None for a plugin that is not ready."""
        self.assertIsNone(ApiPlugin().manifest)

    def test_api_manifest_from_database_parameters(self):
        """Test that the reconstructed manifest has the original manifest parameters and test values."""
        api_data = self.load_api_plugin().manifest.spec.apiData  # type: ignore[union-attr]
        self.assertEqual([p.name for p in api_data.parameters], ["kind", "source"])  # type: ignore[union-attr]
        self.assertEqual(api_data.parameters[0].enum, ["list", "dict"])  # type: ignore[index]
        self.assertEqual({tv.name for tv in api_data.testValues}, {"kind", "source"})  # type: ignore[union-attr]

    def test_api_manifest_from_database_recreates_plugin(self):
        """Test that a manifest reconstructed from the database can create an identical plugin."""
        name = "api_recreated"
        self.addCleanup(self.delete_plugin_by_name, name)
        data = json.loads(self.load_api_plugin().manifest.model_dump_json())  # type: ignore[union-attr]
        data["metadata"]["name"] = name
        data.pop("status", None)
        plugin = ApiPlugin(manifest=SAMApiPlugin(**data), user_profile=self.user_profile)
        self.assertEqual(plugin.function_parameters, self.load_api_plugin().function_parameters)
        self.assertEqual(plugin.plugin_data.headers, self.load_api_plugin().plugin_data.headers)  # type: ignore[union-attr]

    def test_api_to_json_test_values(self):
        """Test that to_json includes the api test values, which the serializer omits."""
        api_data = self.load_api_plugin().to_json()["spec"]["apiData"]  # type: ignore[index]
        self.assertEqual({tv["name"] for tv in api_data["testValues"]}, {"kind", "source"})

    def test_api_to_json(self):
        """Test that to_json includes the API data section."""
        api_data = self.load_api_plugin().to_json()["spec"]["apiData"]  # type: ignore[index]
        self.assertEqual(api_data["endpoint"], API_ENDPOINT)
        self.assertEqual(api_data["method"], "GET")
        self.assertEqual(api_data["connection"], API_CONNECTION_NAME)

    def test_api_to_json_validates_as_manifest(self):
        """Test that to_json produces a valid SAMApiPlugin manifest."""
        self.assertIsInstance(SAMApiPlugin(**self.load_api_plugin().to_json()), SAMApiPlugin)  # type: ignore[arg-type]

    # =========================================================================
    # ApiPlugin: plugin_data_django_model
    # =========================================================================
    def test_api_plugin_data_django_model(self):
        """Test the PluginDataApi Django model dict constructed from the manifest."""
        model = self.api_plugin.plugin_data_django_model
        self.assertIsInstance(model, dict)
        self.assertEqual(model["endpoint"], API_ENDPOINT)  # type: ignore[index]
        self.assertEqual(model["method"], "GET")  # type: ignore[index]
        self.assertEqual(model["connection"], self.api_connection)  # type: ignore[index]
        self.assertEqual(model["plugin"], self.api_plugin.plugin_meta)  # type: ignore[index]

    def test_api_plugin_data_django_model_parameters(self):
        """Test that manifest parameters are recast to the OpenAI function calling schema."""
        parameters = self.api_plugin.plugin_data_django_model["parameters"]  # type: ignore[index]
        self.assertEqual(parameters["type"], "object")
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(parameters["required"], ["kind"])
        self.assertEqual(parameters["properties"]["kind"]["enum"], ["list", "dict"])
        self.assertEqual(parameters["properties"]["kind"]["default"], "list")

    def test_api_plugin_data_django_model_snake_case_keys(self):
        """Test that the Django model dict uses snake_case keys."""
        model = self.api_plugin.plugin_data_django_model
        self.assertIn("url_params", model)  # type: ignore[operator]
        self.assertIn("test_values", model)  # type: ignore[operator]
        self.assertNotIn("urlParams", model)  # type: ignore[operator]

    def test_api_plugin_data_django_model_without_manifest(self):
        """Test that the Django model dict is None without a manifest."""
        self.assertIsNone(self.load_api_plugin().plugin_data_django_model)

    def test_api_missing_connection_raises(self):
        """Test that a nonexistent connection raises SmarterApiPluginError and leaves nothing behind."""
        name = "api_missing_connection"
        self.addCleanup(self.delete_plugin_by_name, name)
        with self.assertRaises(SmarterApiPluginError) as context:
            ApiPlugin(manifest=self.api_manifest(name, connection="no_such_connection"), user_profile=self.user_profile)
        self.assertIn("no_such_connection", str(context.exception))
        self.assertFalse(PluginMeta.objects.filter(user_profile__account=self.account, name=name).exists())

    def test_api_placeholder_not_in_parameters_raises(self):
        """Test that an endpoint placeholder without a matching parameter is rejected."""
        name = "api_bad_placeholder"
        self.addCleanup(self.delete_plugin_by_name, name)
        manifest = self.api_manifest_dict(name)
        manifest["spec"]["apiData"]["endpoint"] = "/api/v1/{not_a_parameter}/"
        with self.assertRaises(SmarterValueError):
            ApiPlugin(manifest=SAMApiPlugin(**manifest), user_profile=self.user_profile)

    # =========================================================================
    # ApiPlugin: example manifest
    # =========================================================================
    def test_api_example_manifest(self):
        """Test that the example manifest is a valid SAMApiPlugin."""
        example = ApiPlugin.example_manifest()
        self.assertIsInstance(example, dict)
        self.assertEqual(example["kind"], API_MANIFEST_KIND)
        self.assertIsInstance(SAMApiPlugin(**example), SAMApiPlugin)

    def test_api_example_manifest_test_values_match_parameters(self):
        """Test that the example manifest provides a test value for every parameter."""
        api_data = ApiPlugin.example_manifest()["spec"]["apiData"]
        self.assertSetEqual({p["name"] for p in api_data["parameters"]}, {tv["name"] for tv in api_data["testValues"]})

    def test_api_example_manifest_tags(self):
        """Test that the example manifest is tagged as an api plugin."""
        self.assertIn("api", ApiPlugin.example_manifest()["metadata"]["tags"])

    # =========================================================================
    # ApiPlugin: tool calls, request construction
    # =========================================================================
    def test_api_tool_call_get(self):
        """Test the HTTP request sent for a GET tool call."""
        retval, request = self.api_call(self.load_api_plugin(), {"kind": "list"}, json_data=[{"id": 1}])
        self.assertEqual(retval, [{"id": 1}])
        request.assert_called_once()
        method, url = request.call_args.args
        self.assertEqual(method, "GET")
        self.assertEqual(url, "http://localhost:9357/api/v1/tests/unauthenticated/list/")
        self.assertEqual(request.call_args.kwargs["params"], {"source": "smarter"})
        self.assertNotIn("json", request.call_args.kwargs)

    def test_api_tool_call_json_string_args(self):
        """Test a tool call with a JSON string of arguments, as sent by OpenAI."""
        _, request = self.api_call(self.load_api_plugin(), '{"kind": "dict"}')
        self.assertTrue(request.call_args.args[1].endswith("/unauthenticated/dict/"))

    def test_api_tool_call_list_args(self):
        """Test a tool call with a list of argument dicts, which are merged."""
        _, request = self.api_call(self.load_api_plugin(), [{"kind": "dict"}, {"page": 2}])
        self.assertTrue(request.call_args.args[1].endswith("/unauthenticated/dict/"))
        self.assertEqual(request.call_args.kwargs["params"], {"source": "smarter", "page": 2})

    def test_api_tool_call_path_placeholder_is_url_encoded(self):
        """Test that path placeholder values are URL encoded, including slashes."""
        _, request = self.api_call(self.load_api_plugin(), {"kind": "a b/c?d=e"})
        self.assertTrue(request.call_args.args[1].endswith("/unauthenticated/a%20b%2Fc%3Fd%3De/"))

    def test_api_tool_call_path_placeholder_not_in_query_string(self):
        """Test that arguments consumed by the path are not repeated in the query string."""
        _, request = self.api_call(self.load_api_plugin(), {"kind": "list"})
        self.assertNotIn("kind", request.call_args.kwargs["params"])

    def test_api_tool_call_repeated_placeholder(self):
        """Test that a placeholder used twice in the endpoint is interpolated twice."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.endpoint = "/api/{kind}/{kind}/"  # type: ignore[union-attr]
        _, request = self.api_call(plugin, {"kind": "list"})
        self.assertTrue(request.call_args.args[1].endswith("/api/list/list/"))

    def test_api_tool_call_missing_placeholder_raises(self):
        """Test that a missing path placeholder value raises."""
        with self.assertRaises(SmarterApiPluginError) as context:
            self.api_call(self.load_api_plugin(), {"source": "x"})
        self.assertIn("kind", str(context.exception))

    def test_api_tool_call_null_placeholder_raises(self):
        """Test that a null path placeholder value raises."""
        with self.assertRaises(SmarterApiPluginError):
            self.api_call(self.load_api_plugin(), {"kind": None})

    def test_api_tool_call_args_override_static_url_params(self):
        """Test that tool call arguments override static url params of the same name."""
        _, request = self.api_call(self.load_api_plugin(), {"kind": "list", "source": "llm"})
        self.assertEqual(request.call_args.kwargs["params"], {"source": "llm"})

    def test_api_tool_call_null_args_are_dropped(self):
        """Test that null arguments are omitted, leaving static url params intact."""
        _, request = self.api_call(self.load_api_plugin(), {"kind": "list", "source": None, "page": None})
        self.assertEqual(request.call_args.kwargs["params"], {"source": "smarter"})

    def test_api_tool_call_no_static_url_params(self):
        """Test a tool call for a plugin without static url params."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.url_params = None  # type: ignore[union-attr]
        _, request = self.api_call(plugin, {"kind": "list", "page": 1})
        self.assertEqual(request.call_args.kwargs["params"], {"page": 1})

    def test_api_tool_call_headers(self):
        """Test that static manifest headers are sent."""
        _, request = self.api_call(self.load_api_plugin(), {"kind": "list"})
        headers = request.call_args.kwargs["headers"]
        self.assertEqual(headers["Accept"], "application/json")
        self.assertEqual(headers["X-Request-ID"], "testRequestId")

    def test_api_tool_call_connection_auth_overrides_manifest_header(self):
        """Test that the connection's token auth overrides a manifest Authorization header."""
        _, request = self.api_call(self.load_api_plugin(), {"kind": "list"})
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], f"Bearer {self.api_key}")

    def test_api_tool_call_timeout(self):
        """Test that the connection timeout is applied."""
        _, request = self.api_call(self.load_api_plugin(), {"kind": "list"})
        self.assertEqual(request.call_args.kwargs["timeout"], self.api_connection.timeout)

    def test_api_tool_call_method_is_case_insensitive(self):
        """Test that a lowercase method is normalized."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.method = "get"  # type: ignore[union-attr]
        _, request = self.api_call(plugin, {"kind": "list"})
        self.assertEqual(request.call_args.args[0], "GET")

    def test_api_tool_call_no_method_defaults_to_get(self):
        """Test that a plugin without a method sends GET."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.method = None  # type: ignore[union-attr]
        _, request = self.api_call(plugin, {"kind": "list"})
        self.assertEqual(request.call_args.args[0], "GET")

    def test_api_tool_call_post_args_go_to_body(self):
        """Test that POST arguments are merged into the JSON body."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.method = "POST"  # type: ignore[union-attr]
        plugin.plugin_data.body = {"static": 1, "page": 0}  # type: ignore[union-attr]
        _, request = self.api_call(plugin, {"kind": "list", "page": 2})
        self.assertEqual(request.call_args.args[0], "POST")
        self.assertEqual(request.call_args.kwargs["json"], {"static": 1, "page": 2})
        self.assertEqual(request.call_args.kwargs["params"], {"source": "smarter"})

    def test_api_tool_call_post_without_static_body(self):
        """Test that POST arguments form the body when there is no static body."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.method = "POST"  # type: ignore[union-attr]
        _, request = self.api_call(plugin, {"kind": "list", "page": 2})
        self.assertEqual(request.call_args.kwargs["json"], {"page": 2})

    def test_api_tool_call_post_does_not_mutate_static_body(self):
        """Test that merging arguments does not modify the plugin's static body."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.method = "POST"  # type: ignore[union-attr]
        plugin.plugin_data.body = {"static": 1}  # type: ignore[union-attr]
        self.api_call(plugin, {"kind": "list", "page": 2})
        self.assertEqual(plugin.plugin_data.body, {"static": 1})  # type: ignore[union-attr]

    def test_api_tool_call_post_with_list_body(self):
        """Test that POST arguments go to the query string when the static body is a list."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.method = "POST"  # type: ignore[union-attr]
        plugin.plugin_data.body = [1, 2, 3]  # type: ignore[union-attr]
        _, request = self.api_call(plugin, {"kind": "list", "page": 2})
        self.assertEqual(request.call_args.kwargs["json"], [1, 2, 3])
        self.assertEqual(request.call_args.kwargs["params"], {"source": "smarter", "page": 2})

    def test_api_tool_call_put_and_patch_args_go_to_body(self):
        """Test that PUT and PATCH arguments are merged into the JSON body."""
        for method in ("PUT", "PATCH"):
            plugin = self.load_api_plugin()
            plugin.plugin_data.method = method  # type: ignore[union-attr]
            _, request = self.api_call(plugin, {"kind": "list", "page": 2})
            self.assertEqual(request.call_args.args[0], method)
            self.assertEqual(request.call_args.kwargs["json"], {"page": 2})

    def test_api_tool_call_delete_args_go_to_query_string(self):
        """Test that DELETE arguments go to the query string and no body is sent."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.method = "DELETE"  # type: ignore[union-attr]
        plugin.plugin_data.body = {"static": 1}  # type: ignore[union-attr]
        _, request = self.api_call(plugin, {"kind": "list", "page": 2})
        self.assertEqual(request.call_args.args[0], "DELETE")
        self.assertEqual(request.call_args.kwargs["params"], {"source": "smarter", "page": 2})
        self.assertNotIn("json", request.call_args.kwargs)

    def test_api_tool_call_get_with_static_body_sends_no_body(self):
        """Test that a GET request never sends a body."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.body = {"static": 1}  # type: ignore[union-attr]
        _, request = self.api_call(plugin, {"kind": "list"})
        self.assertNotIn("json", request.call_args.kwargs)

    # =========================================================================
    # ApiPlugin: tool calls, argument validation
    # =========================================================================
    def test_api_tool_call_invalid_json_string(self):
        """Test that a malformed JSON string of arguments raises."""
        with self.assertRaises(SmarterApiPluginError):
            self.api_call(self.load_api_plugin(), "{not json")

    def test_api_tool_call_invalid_args_type(self):
        """Test that arguments of an unsupported type raise."""
        with self.assertRaises(SmarterApiPluginError):
            self.api_call(self.load_api_plugin(), 42)

    def test_api_tool_call_list_of_non_dicts(self):
        """Test that a list containing non-dict arguments raises."""
        with self.assertRaises(SmarterApiPluginError):
            self.api_call(self.load_api_plugin(), ["kind", "list"])

    def test_api_tool_call_empty_args_without_placeholders(self):
        """Test tool calls with empty arguments against an endpoint without placeholders."""
        for function_args in (None, {}, [], ""):
            cache.clear()
            plugin = self.load_api_plugin()
            plugin.plugin_data.endpoint = "/api/v1/tests/unauthenticated/list/"  # type: ignore[union-attr]
            _, request = self.api_call(plugin, function_args)
            self.assertEqual(
                request.call_args.kwargs["params"], {"source": "smarter"}, f"function_args={function_args!r}"
            )

    def test_api_tool_call_no_plugin_data(self):
        """Test that a tool call without plugin data raises."""
        plugin = self.load_api_plugin()
        with mock.patch.object(ApiPlugin, "plugin_data", new_callable=mock.PropertyMock, return_value=None):
            with self.assertRaises(SmarterApiPluginError):
                plugin.tool_call_fetch_plugin_response({"kind": "list"})

    def test_api_tool_call_invalid_connection(self):
        """Test that a tool call with an invalid connection raises."""
        plugin = self.load_api_plugin()
        plugin_data = SimpleNamespace(connection=mock.MagicMock(spec=SqlConnection), endpoint=API_ENDPOINT)
        with mock.patch.object(ApiPlugin, "plugin_data", new_callable=mock.PropertyMock, return_value=plugin_data):
            with self.assertRaises(SmarterApiPluginError):
                plugin.tool_call_fetch_plugin_response({"kind": "list"})

    def test_api_tool_call_endpoint_not_a_string(self):
        """Test that a tool call with a non-string endpoint raises."""
        plugin = self.load_api_plugin()
        plugin_data = SimpleNamespace(connection=self.api_connection, endpoint=None)
        with mock.patch.object(ApiPlugin, "plugin_data", new_callable=mock.PropertyMock, return_value=plugin_data):
            with self.assertRaises(SmarterApiPluginError):
                plugin.tool_call_fetch_plugin_response({"kind": "list"})

    # =========================================================================
    # ApiPlugin: tool calls, responses
    # =========================================================================
    def test_api_tool_call_dict_response(self):
        """Test a tool call that returns a JSON object."""
        retval, _ = self.api_call(self.load_api_plugin(), {"kind": "dict"}, json_data={"id": 1, "name": "x"})
        self.assertEqual(retval, {"id": 1, "name": "x"})

    def test_api_tool_call_list_response_is_limited(self):
        """Test that a list response is truncated to the plugin limit."""
        retval, _ = self.api_call(self.load_api_plugin(), {"kind": "list"}, json_data=list(range(50)))
        self.assertEqual(retval, list(range(10)))

    def test_api_tool_call_dict_response_is_limited(self):
        """Test that the lists in a dict response are truncated and its scalar fields are kept."""
        json_data = {"results": list(range(50)), "count": 50, "next": None}
        retval, _ = self.api_call(self.load_api_plugin(), {"kind": "dict"}, json_data=json_data)
        self.assertEqual(retval, {"results": list(range(10)), "count": 50, "next": None})

    def test_api_tool_call_limit_is_capped(self):
        """Test that the plugin limit is capped at MAX_API_RESULTS."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.limit = MAX_API_RESULTS * 10  # type: ignore[union-attr]
        retval, _ = self.api_call(plugin, {"kind": "list"}, json_data=list(range(MAX_API_RESULTS + 5)))
        self.assertEqual(len(retval), MAX_API_RESULTS)  # type: ignore[arg-type]

    def test_api_tool_call_no_limit_uses_max(self):
        """Test that a plugin without a limit uses MAX_API_RESULTS."""
        plugin = self.load_api_plugin()
        plugin.plugin_data.limit = None  # type: ignore[union-attr]
        retval, _ = self.api_call(plugin, {"kind": "list"}, json_data=list(range(MAX_API_RESULTS + 5)))
        self.assertEqual(len(retval), MAX_API_RESULTS)  # type: ignore[arg-type]

    def test_api_tool_call_empty_response_returns_empty_string(self):
        """Test that an empty response returns an empty string."""
        for empty in ([], {}):
            cache.clear()
            retval, _ = self.api_call(self.load_api_plugin(), {"kind": "list"}, json_data=empty)
            self.assertEqual(retval, "", f"response={empty!r}")

    def test_api_tool_call_http_error_returns_empty_string(self):
        """Test that an HTTP error returns an empty string."""
        for status_code in (400, 401, 403, 404, 500, 503):
            cache.clear()
            retval, _ = self.api_call(self.load_api_plugin(), {"kind": "list"}, status_code=status_code)
            self.assertEqual(retval, "", f"status_code={status_code}")

    def test_api_tool_call_connection_error_returns_empty_string(self):
        """Test that a connection error returns an empty string."""
        for error in (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            cache.clear()
            with mock.patch(API_REQUEST_PATCH, side_effect=error("boom")):
                self.assertEqual(self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "list"}), "")

    def test_api_tool_call_non_ok_success_status_returns_empty_string(self):
        """Test that a 2xx status other than 200 is treated as a failure by the connection."""
        retval, _ = self.api_call(self.load_api_plugin(), {"kind": "list"}, status_code=204)
        self.assertEqual(retval, "")

    # =========================================================================
    # ApiPlugin: tool calls, caching
    # =========================================================================
    def test_api_tool_call_get_is_cached(self):
        """Test that identical GET tool calls are served from the cache."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([{"id": 1}])) as request:
            first = self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "list"})
            second = self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "list"})
        self.assertEqual(first, second)
        request.assert_called_once()

    def test_api_tool_call_get_different_args_are_not_cached_together(self):
        """Test that GET tool calls with different arguments are cached separately."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([{"id": 1}])) as request:
            self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "list"})
            self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "dict"})
            self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "list", "page": 2})
        self.assertEqual(request.call_count, 3)

    def test_api_tool_call_get_cache_is_per_connection(self):
        """Test that identical requests against different connections are cached separately."""
        other = self.new_api_plugin("api_other_connection", connection=API_CONNECTION_NAME_2)
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([{"id": 1}])) as request:
            self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "list"})
            other.tool_call_fetch_plugin_response({"kind": "list"})
        self.assertEqual(request.call_count, 2)

    def test_api_tool_call_get_cache_is_per_limit(self):
        """Test that identical requests with different limits are cached separately."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response(list(range(50)))) as request:
            first = self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "list"})
            plugin = self.load_api_plugin()
            plugin.plugin_data.limit = 3  # type: ignore[union-attr]
            second = plugin.tool_call_fetch_plugin_response({"kind": "list"})
        self.assertEqual(request.call_count, 2)
        self.assertEqual(len(first), 10)  # type: ignore[arg-type]
        self.assertEqual(len(second), 3)  # type: ignore[arg-type]

    def test_api_tool_call_non_get_is_not_cached(self):
        """Test that POST, PUT, PATCH and DELETE tool calls are never cached."""
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with mock.patch(API_REQUEST_PATCH, return_value=mock_response([{"id": 1}])) as request:
                for _ in range(2):
                    plugin = self.load_api_plugin()
                    plugin.plugin_data.method = method  # type: ignore[union-attr]
                    plugin.tool_call_fetch_plugin_response({"kind": "list"})
            self.assertEqual(request.call_count, 2, f"method={method}")

    def test_api_tool_call_failure_is_not_cached(self):
        """Test that a failed GET request is retried on the next tool call."""
        self.api_call(self.load_api_plugin(), {"kind": "list"}, status_code=500)
        retval, request = self.api_call(self.load_api_plugin(), {"kind": "list"}, json_data=[{"id": 1}])
        request.assert_called_once()
        self.assertEqual(retval, [{"id": 1}])

    # =========================================================================
    # ApiPlugin: tool calls against the live Smarter test api
    # =========================================================================
    @skipUnless(LIVE_API_AVAILABLE, f"{LIVE_API_PROBE_URL} is not reachable")
    def test_api_tool_call_live_list(self):
        """Test a real GET request that returns a JSON list."""
        retval = self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "list"})
        self.assertIsInstance(retval, list)
        self.assertGreater(len(retval), 0)  # type: ignore[arg-type]
        self.assertLessEqual(len(retval), 10)  # type: ignore[arg-type]

    @skipUnless(LIVE_API_AVAILABLE, f"{LIVE_API_PROBE_URL} is not reachable")
    def test_api_tool_call_live_dict(self):
        """Test a real GET request that returns a JSON object."""
        retval = self.load_api_plugin().tool_call_fetch_plugin_response('{"kind": "dict"}')
        self.assertIsInstance(retval, dict)

    @skipUnless(LIVE_API_AVAILABLE, f"{LIVE_API_PROBE_URL} is not reachable")
    def test_api_tool_call_live_not_found(self):
        """Test a real GET request to an endpoint that does not exist."""
        retval = self.load_api_plugin().tool_call_fetch_plugin_response({"kind": "no-such-endpoint"})
        self.assertEqual(retval, "")

    # =========================================================================
    # ApiConnection.execute_query, which backs the ApiPlugin
    # =========================================================================
    def fresh_api_connection(self) -> ApiConnection:
        """Return a fresh, unsaved-changes-safe instance of the shared ApiConnection."""
        return ApiConnection.objects.get(pk=self.api_connection.pk)

    def test_api_connection_execute_query_defaults(self):
        """Test that execute_query is backward compatible with its original positional signature."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([1, 2, 3])) as request:
            retval = self.fresh_api_connection().execute_query("/x/", {"a": 1}, 2)
        self.assertEqual(retval, [1, 2])
        self.assertEqual(request.call_args.args, ("GET", "http://localhost:9357/x/"))
        self.assertEqual(request.call_args.kwargs["params"], {"a": 1})

    def test_api_connection_execute_query_keyword_only(self):
        """Test that the new request options are keyword-only."""
        with self.assertRaises(TypeError):
            self.fresh_api_connection().execute_query("/x/", None, None, "POST")  # type: ignore[misc]

    def test_api_connection_execute_query_token_auth(self):
        """Test that token auth sends the decrypted api key as a bearer token."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([1])) as request:
            self.fresh_api_connection().execute_query("/x/")
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], f"Bearer {self.api_key}")

    def test_api_connection_execute_query_does_not_send_secret_name(self):
        """Test that the Secret's name is never sent in place of its value."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([1])) as request:
            self.fresh_api_connection().execute_query("/x/")
        self.assertNotIn(self.api_secret.name, request.call_args.kwargs["headers"]["Authorization"])

    def test_api_connection_execute_query_basic_auth(self):
        """Test that basic auth sends the decrypted api key."""
        connection = self.fresh_api_connection()
        connection.auth_method = "basic"
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([1])) as request:
            connection.execute_query("/x/")
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], f"Basic {self.api_key}")

    def test_api_connection_execute_query_no_auth(self):
        """Test that no Authorization header is added when auth is none, and a caller's header is kept."""
        connection = self.fresh_api_connection()
        connection.auth_method = "none"
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([1])) as request:
            connection.execute_query("/x/", headers={"Authorization": "Bearer caller", "Accept": "text/plain"})
        self.assertEqual(
            request.call_args.kwargs["headers"], {"Authorization": "Bearer caller", "Accept": "text/plain"}
        )

    def test_api_connection_execute_query_does_not_mutate_headers(self):
        """Test that the caller's headers dict is not modified."""
        headers = {"Accept": "application/json"}
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([1])):
            self.fresh_api_connection().execute_query("/x/", headers=headers)
        self.assertEqual(headers, {"Accept": "application/json"})

    def test_api_connection_execute_query_body_methods(self):
        """Test that a body is sent only for POST, PUT and PATCH."""
        expectations = {"GET": False, "DELETE": False, "POST": True, "PUT": True, "PATCH": True}
        for method, sends_body in expectations.items():
            with mock.patch(API_REQUEST_PATCH, return_value=mock_response([1])) as request:
                self.fresh_api_connection().execute_query("/x/", method=method, body={"a": 1})
            self.assertEqual(request.call_args.args[0], method)
            self.assertEqual("json" in request.call_args.kwargs, sends_body, f"method={method}")

    def test_api_connection_execute_query_lowercase_method(self):
        """Test that the method is normalized to uppercase."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([1])) as request:
            self.fresh_api_connection().execute_query("/x/", method="post", body={"a": 1})
        self.assertEqual(request.call_args.args[0], "POST")
        self.assertEqual(request.call_args.kwargs["json"], {"a": 1})

    def test_api_connection_execute_query_no_limit(self):
        """Test that the response is returned in full without a limit."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response(list(range(50)))):
            self.assertEqual(self.fresh_api_connection().execute_query("/x/"), list(range(50)))

    def test_api_connection_execute_query_dict_limit_keeps_scalars(self):
        """Test that limiting a dict response keeps its non-list fields."""
        json_data = {"results": list(range(5)), "count": 5, "meta": {"page": 1}}
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response(json_data)):
            retval = self.fresh_api_connection().execute_query("/x/", limit=2)
        self.assertEqual(retval, {"results": [0, 1], "count": 5, "meta": {"page": 1}})

    def test_api_connection_execute_query_http_error(self):
        """Test that an HTTP error returns False."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response(None, 500)):
            self.assertFalse(self.fresh_api_connection().execute_query("/x/"))

    def test_api_connection_execute_query_connection_error(self):
        """Test that a connection error returns False rather than raising."""
        for error in (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ):
            with mock.patch(API_REQUEST_PATCH, side_effect=error("boom")):
                self.assertFalse(self.fresh_api_connection().execute_query("/x/"), f"error={error.__name__}")

    def test_api_connection_execute_query_url_join(self):
        """Test that endpoints are joined to the connection base url."""
        with mock.patch(API_REQUEST_PATCH, return_value=mock_response([1])) as request:
            self.fresh_api_connection().execute_query("api/v1/x/")
        self.assertEqual(request.call_args.args[1], "http://localhost:9357/api/v1/x/")
