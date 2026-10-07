# pylint: disable=too-many-lines,protected-access
"""
Unit tests for :py:class:`smarter.apps.plugin.plugin.sql.SqlPlugin`.

.. note::

    The tool call tests run real queries against the SqlConnection defined in
    ``./data/sql-connection.yaml``, so these tests must run inside the docker network.
"""

from types import SimpleNamespace
from unittest import mock

from django.core.cache import cache

from smarter.apps.connection.models import SqlConnection
from smarter.apps.plugin.manifest.models.sql_plugin.const import (
    MANIFEST_KIND as SQL_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.models import PluginDataSql, PluginMeta
from smarter.apps.plugin.plugin.sql import (
    MAX_SQL_QUERY_LENGTH,
    SmarterSqlPluginError,
    SqlPlugin,
)
from smarter.apps.plugin.serializers import PluginSqlSerializer
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json

from .base_classes import (
    SQL_CONNECTION_NAME,
    SQL_CONNECTION_NAME_2,
    SQL_PLUGIN_NAME,
    SQL_QUERY,
    PluginTestBase,
)


# pylint: disable=too-many-public-methods
class TestSqlPlugin(PluginTestBase):
    """Test SqlPlugin, using the shared SqlPlugin fixture."""

    api_fixtures = False

    # =========================================================================
    # fixtures
    # =========================================================================
    def test_000_fixtures(self):
        """Test the class fixtures themselves, lest we get ahead of ourselves."""
        self.assertTrue(self.ready)
        self.assertIsInstance(self.sql_connection, SqlConnection)
        self.assertIsInstance(self.sql_connection_2, SqlConnection)
        self.assertIsInstance(self.sql_plugin, SqlPlugin)
        self.assertTrue(self.sql_plugin.ready)
        self.assertEqual(self.sql_plugin_yaml["spec"]["sqlData"]["sqlQuery"].strip(), SQL_QUERY)

    # =========================================================================
    # SqlPlugin: class structure
    # =========================================================================
    def test_sql_class_attributes(self):
        """Test the SqlPlugin class attributes."""
        self.assertIs(SqlPlugin.SAMPluginType, SAMSqlPlugin)
        self.assertEqual(self.sql_plugin.kind, SQL_MANIFEST_KIND)
        self.assertIs(self.sql_plugin.plugin_data_class, PluginDataSql)
        self.assertIs(self.sql_plugin.plugin_data_serializer_class, PluginSqlSerializer)

    def test_sql_plugin_data_serializer(self):
        """Test the SqlPlugin data serializer."""
        serializer = self.load_sql_plugin().plugin_data_serializer
        self.assertIsInstance(serializer, PluginSqlSerializer)
        self.assertIn(SQL_QUERY, json.dumps(serializer.data))  # type: ignore[union-attr]

    def test_sql_plugin_data(self):
        """Test the SqlPlugin data Django model."""
        plugin_data = self.load_sql_plugin().plugin_data
        self.assertIsInstance(plugin_data, PluginDataSql)
        self.assertEqual(plugin_data.sql_query, SQL_QUERY)  # type: ignore[union-attr]
        self.assertEqual(plugin_data.limit, self.sql_plugin_yaml["spec"]["sqlData"]["limit"])  # type: ignore[union-attr]
        self.assertEqual(plugin_data.connection, self.sql_connection)  # type: ignore[union-attr]
        self.assertEqual(plugin_data.description, self.sql_plugin_yaml["metadata"]["description"])  # type: ignore[union-attr]

    def test_sql_plugin_data_test_values(self):
        """Test that the SqlPlugin test values are persisted."""
        test_values = self.load_sql_plugin().plugin_data.test_values  # type: ignore[union-attr]
        self.assertEqual({tv["name"] for tv in test_values}, {"username", "unit"})

    def test_sql_plugin_data_is_memoized(self):
        """Test that plugin_data returns the same instance on repeat access."""
        plugin = self.load_sql_plugin()
        self.assertIs(plugin.plugin_data, plugin.plugin_data)

    def test_sql_manifest_from_database(self):
        """Test that the manifest is reconstructed from the database when not provided."""
        plugin = self.load_sql_plugin()
        self.assertIsNone(plugin._manifest)
        manifest = plugin.manifest
        self.assertIsInstance(manifest, SAMSqlPlugin)
        self.assertEqual(manifest.metadata.name, SQL_PLUGIN_NAME)  # type: ignore[union-attr]
        self.assertEqual(manifest.spec.sqlData.sqlQuery, SQL_QUERY)  # type: ignore[union-attr]
        self.assertEqual(manifest.spec.connection, SQL_CONNECTION_NAME)  # type: ignore[union-attr]

    def test_sql_manifest_not_ready(self):
        """Test that the manifest is None for a plugin that is not ready."""
        self.assertIsNone(SqlPlugin().manifest)

    def test_sql_manifest_round_trip(self):
        """Test that a manifest reconstructed from the database can recreate the plugin."""
        manifest = self.load_sql_plugin().manifest
        data = json.loads(manifest.model_dump_json())  # type: ignore[union-attr]
        self.assertEqual(data["spec"]["sqlData"]["parameters"][0]["name"], "username")
        self.assertEqual(data["spec"]["sqlData"]["limit"], self.sql_plugin_yaml["spec"]["sqlData"]["limit"])

    def test_sql_manifest_from_database_parameters(self):
        """Test that the reconstructed manifest has the original manifest parameters."""
        parameters = self.load_sql_plugin().manifest.spec.sqlData.parameters  # type: ignore[union-attr]
        self.assertEqual([p.name for p in parameters], ["username", "unit"])  # type: ignore[union-attr]
        self.assertTrue(parameters[0].required)  # type: ignore[index]
        self.assertEqual(parameters[1].enum, ["Celsius", "Fahrenheit"])  # type: ignore[index]

    def test_sql_manifest_from_database_recreates_plugin(self):
        """Test that a manifest reconstructed from the database can create an identical plugin."""
        name = "sql_recreated"
        self.addCleanup(self.delete_plugin_by_name, name)
        data = json.loads(self.load_sql_plugin().manifest.model_dump_json())  # type: ignore[union-attr]
        data["metadata"]["name"] = name
        data.pop("status", None)
        plugin = SqlPlugin(manifest=SAMSqlPlugin(**data), user_profile=self.user_profile)
        self.assertEqual(plugin.function_parameters, self.load_sql_plugin().function_parameters)
        self.assertEqual(plugin.plugin_data.sql_query, SQL_QUERY)  # type: ignore[union-attr]

    def test_sql_to_json(self):
        """Test that to_json includes the SQL data section."""
        sql_data = self.load_sql_plugin().to_json()["spec"]["sqlData"]  # type: ignore[index]
        self.assertEqual(sql_data["sqlQuery"], SQL_QUERY)
        self.assertEqual(sql_data["connection"], SQL_CONNECTION_NAME)

    def test_sql_to_json_validates_as_manifest(self):
        """Test that to_json produces a valid SAMSqlPlugin manifest."""
        self.assertIsInstance(SAMSqlPlugin(**self.load_sql_plugin().to_json()), SAMSqlPlugin)  # type: ignore[arg-type]

    # =========================================================================
    # SqlPlugin: plugin_data_django_model
    # =========================================================================
    def test_sql_plugin_data_django_model(self):
        """Test the PluginDataSql Django model dict constructed from the manifest."""
        model = self.sql_plugin.plugin_data_django_model
        self.assertIsInstance(model, dict)
        self.assertEqual(model["sql_query"], SQL_QUERY)  # type: ignore[index]
        self.assertEqual(model["connection"], self.sql_connection)  # type: ignore[index]
        self.assertEqual(model["plugin"], self.sql_plugin.plugin_meta)  # type: ignore[index]
        self.assertEqual(model["description"], self.sql_plugin_yaml["metadata"]["description"])  # type: ignore[index]

    def test_sql_plugin_data_django_model_parameters(self):
        """Test that manifest parameters are recast to the OpenAI function calling schema."""
        parameters = self.sql_plugin.plugin_data_django_model["parameters"]  # type: ignore[index]
        self.assertEqual(parameters["type"], "object")
        self.assertFalse(parameters["additionalProperties"])
        self.assertEqual(parameters["required"], ["username"])
        self.assertEqual(
            parameters["properties"]["username"],
            {"type": "string", "description": "The username to query.", "default": "admin"},
        )
        self.assertEqual(parameters["properties"]["unit"]["enum"], ["Celsius", "Fahrenheit"])

    def test_sql_plugin_data_django_model_snake_case_keys(self):
        """Test that the Django model dict uses snake_case keys."""
        model = self.sql_plugin.plugin_data_django_model
        self.assertIn("test_values", model)  # type: ignore[operator]
        self.assertNotIn("testValues", model)  # type: ignore[operator]
        self.assertNotIn("sqlQuery", model)  # type: ignore[operator]

    def test_sql_plugin_data_django_model_without_manifest(self):
        """Test that the Django model dict is None without a manifest."""
        self.assertIsNone(self.load_sql_plugin().plugin_data_django_model)

    def test_sql_plugin_data_django_model_without_parameters(self):
        """Test the Django model dict when the manifest has no parameters."""
        name = "sql_no_parameters"
        self.addCleanup(self.delete_plugin_by_name, name)
        manifest = self.sql_manifest_dict(name, sql_query="SELECT 1 AS one;")
        manifest["spec"]["sqlData"]["parameters"] = None
        manifest["spec"]["sqlData"]["testValues"] = None
        plugin = SqlPlugin(manifest=SAMSqlPlugin(**manifest), user_profile=self.user_profile)
        self.assertTrue(plugin.ready)
        self.assertIsNone(plugin.plugin_data_django_model["parameters"])  # type: ignore[index]
        self.assertEqual(self.sql_rows(plugin, {}), [{"one": 1}])

    def test_sql_missing_connection_raises(self):
        """Test that a nonexistent connection raises SmarterSqlPluginError and leaves nothing behind."""
        name = "sql_missing_connection"
        self.addCleanup(self.delete_plugin_by_name, name)
        with self.assertRaises(SmarterSqlPluginError) as context:
            SqlPlugin(manifest=self.sql_manifest(name, connection="no_such_connection"), user_profile=self.user_profile)
        self.assertIn("no_such_connection", str(context.exception))
        self.assertFalse(PluginMeta.objects.filter(user_profile__account=self.account, name=name).exists())

    def test_sql_connection_of_another_account_is_not_found(self):
        """Test that a SqlPlugin cannot use another account's connection by name."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.account.models import AccountContact
        from smarter.apps.account.tests.factories import admin_user_factory

        other_user, other_account, other_user_profile = admin_user_factory()

        def cleanup():
            # do NOT use factory_account_teardown() here. it also sweeps every
            # test UserProfile and Account, including this class's fixtures.
            AccountContact.objects.filter(account=other_account).delete()
            PluginMeta.objects.filter(user_profile=other_user_profile).delete()
            other_user_profile.delete()
            other_user.delete()
            other_account.delete()

        self.addCleanup(cleanup)
        name = "sql_other_account"
        with self.assertRaises(SmarterSqlPluginError):
            SqlPlugin(manifest=self.sql_manifest(name), user_profile=other_user_profile)

    def test_sql_placeholder_not_in_parameters_raises(self):
        """Test that a query placeholder without a matching parameter is rejected."""
        name = "sql_bad_placeholder"
        self.addCleanup(self.delete_plugin_by_name, name)
        with self.assertRaises(SmarterValueError):
            SqlPlugin(
                manifest=self.sql_manifest(name, sql_query="SELECT {not_a_parameter} AS x;"),
                user_profile=self.user_profile,
            )

    # =========================================================================
    # SqlPlugin: example manifest
    # =========================================================================
    def test_sql_example_manifest(self):
        """Test that the example manifest is a valid SAMSqlPlugin."""
        example = SqlPlugin.example_manifest()
        self.assertIsInstance(example, dict)
        self.assertEqual(example["kind"], SQL_MANIFEST_KIND)
        self.assertIsInstance(SAMSqlPlugin(**example), SAMSqlPlugin)

    def test_sql_example_manifest_test_values_match_parameters(self):
        """Test that the example manifest provides a test value for every parameter."""
        sql_data = SqlPlugin.example_manifest()["spec"]["sqlData"]
        self.assertSetEqual({p["name"] for p in sql_data["parameters"]}, {tv["name"] for tv in sql_data["testValues"]})

    def test_sql_example_manifest_placeholders_match_parameters(self):
        """Test that every placeholder in the example query is a declared parameter."""
        # pylint: disable=import-outside-toplevel
        import re

        sql_data = SqlPlugin.example_manifest()["spec"]["sqlData"]
        placeholders = set(re.findall(r"\{(\w+)\}", sql_data["sqlQuery"]))
        self.assertTrue(placeholders.issubset({p["name"] for p in sql_data["parameters"]}))

    # =========================================================================
    # SqlPlugin: tool calls against the remote database
    # =========================================================================
    def test_sql_tool_call_dict_args(self):
        """Test a tool call with a dict of arguments."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": "admin", "unit": "Celsius"})
        self.assertEqual(rows, [{"username": "admin", "unit": "Celsius"}])

    def test_sql_tool_call_json_string_args(self):
        """Test a tool call with a JSON string of arguments, as sent by OpenAI."""
        rows = self.sql_rows(self.load_sql_plugin(), '{"username": "admin", "unit": "Fahrenheit"}')
        self.assertEqual(rows, [{"username": "admin", "unit": "Fahrenheit"}])

    def test_sql_tool_call_list_args(self):
        """Test a tool call with a list of argument dicts, which are merged."""
        rows = self.sql_rows(self.load_sql_plugin(), [{"username": "admin"}, {"unit": "Celsius"}])
        self.assertEqual(rows, [{"username": "admin", "unit": "Celsius"}])

    def test_sql_tool_call_list_args_later_wins(self):
        """Test that later dicts in a list of arguments take precedence."""
        rows = self.sql_rows(self.load_sql_plugin(), [{"username": "first"}, {"username": "second"}])
        self.assertEqual(rows[0]["username"], "second")

    def test_sql_tool_call_missing_args_are_null(self):
        """Test that arguments that are not provided are interpolated as NULL."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": "admin"})
        self.assertEqual(rows, [{"username": "admin", "unit": None}])

    def test_sql_tool_call_null_args(self):
        """Test that null arguments are interpolated as NULL."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": None, "unit": None})
        self.assertEqual(rows, [{"username": None, "unit": None}])

    def test_sql_tool_call_empty_args(self):
        """Test tool calls with empty arguments."""
        for function_args in (None, {}, [], ""):
            rows = self.sql_rows(self.load_sql_plugin(), function_args)
            self.assertEqual(rows, [{"username": None, "unit": None}], f"function_args={function_args!r}")

    def test_sql_tool_call_numeric_args(self):
        """Test that numeric arguments are interpolated without quotes."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": 42, "unit": 1.5})
        self.assertEqual(rows[0]["username"], 42)
        self.assertEqual(float(rows[0]["unit"]), 1.5)

    def test_sql_tool_call_escapes_single_quotes(self):
        """Test that single quotes in arguments are escaped."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": "O'Brien", "unit": "it''s"})
        self.assertEqual(rows, [{"username": "O'Brien", "unit": "it''s"}])

    def test_sql_tool_call_injection_via_quote(self):
        """Test that a quote-based SQL injection attempt is returned as a literal value."""
        attack = "x' UNION SELECT user(), version() -- "
        rows = self.sql_rows(self.load_sql_plugin(), {"username": attack, "unit": "Celsius"})
        self.assertEqual(rows, [{"username": attack, "unit": "Celsius"}])

    def test_sql_tool_call_injection_via_backslash_quote(self):
        """Test that a backslash-quote SQL injection attempt is returned as a literal value."""
        attack = "x\\' UNION SELECT user(), version() -- "
        rows = self.sql_rows(self.load_sql_plugin(), {"username": attack, "unit": "Celsius"})
        self.assertEqual(rows, [{"username": attack, "unit": "Celsius"}])

    def test_sql_tool_call_injection_via_trailing_backslash(self):
        """Test that a trailing backslash cannot escape the closing quote."""
        attack = "x\\"
        rows = self.sql_rows(self.load_sql_plugin(), {"username": attack, "unit": " UNION SELECT 1, 2 -- "})
        self.assertEqual(rows, [{"username": attack, "unit": " UNION SELECT 1, 2 -- "}])

    def test_sql_tool_call_preserves_backslashes(self):
        """Test that backslashes in arguments are preserved."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": "C:\\Users\\admin", "unit": "a\\nb"})
        self.assertEqual(rows, [{"username": "C:\\Users\\admin", "unit": "a\\nb"}])

    def test_sql_tool_call_boolean_args(self):
        """Test that boolean arguments are interpolated as SQL booleans."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": True, "unit": False})
        self.assertEqual(rows, [{"username": 1, "unit": 0}])

    def test_sql_tool_call_list_and_dict_args_are_quoted(self):
        """Test that list and dict arguments are JSON encoded and quoted, never interpolated raw."""
        attack = ["') UNION SELECT user(), version() -- "]
        rows = self.sql_rows(self.load_sql_plugin(), {"username": attack, "unit": {"a": "b"}})
        self.assertEqual(json.loads(rows[0]["username"]), attack)
        self.assertEqual(json.loads(rows[0]["unit"]), {"a": "b"})

    def test_sql_tool_call_backslashes_escaped_only_for_mysql(self):
        """Test that backslashes are escaped for MySQL and MariaDB, and only for them."""
        expectations = {
            "django.db.backends.mysql": "SELECT 'a\\\\b' AS username, NULL AS unit;",
            "django.db.backends.postgresql": "SELECT 'a\\b' AS username, NULL AS unit;",
            "django.db.backends.sqlite3": "SELECT 'a\\b' AS username, NULL AS unit;",
        }
        for db_engine, expected_sql in expectations.items():
            cache.clear()
            plugin = self.load_sql_plugin()
            plugin.plugin_data.connection.db_engine = db_engine  # type: ignore[union-attr]
            with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
                plugin.tool_call_fetch_plugin_response({"username": "a\\b"})
            self.assertEqual(execute_query.call_args.kwargs["sql"], expected_sql, f"db_engine={db_engine}")

    def test_sql_tool_call_newlines_in_args_are_preserved(self):
        """Test that newlines inside argument values are not normalized away."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": "line 1\nline 2", "unit": "Celsius"})
        self.assertEqual(rows[0]["username"], "line 1\nline 2")

    def test_sql_tool_call_braces_in_args_are_not_interpolated(self):
        """Test that placeholders inside argument values are not interpolated a second time."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": "{unit}", "unit": "Celsius"})
        self.assertEqual(rows, [{"username": "{unit}", "unit": "Celsius"}])

    def test_sql_tool_call_unicode_args(self):
        """Test that unicode arguments round trip."""
        rows = self.sql_rows(self.load_sql_plugin(), {"username": "José", "unit": "°C"})
        self.assertEqual(rows, [{"username": "José", "unit": "°C"}])

    def test_sql_tool_call_multiline_query(self):
        """Test that a multi-line query with a folded trailing newline executes."""
        name = "sql_multiline"
        plugin = self.new_sql_plugin(name, sql_query="SELECT {username} AS username,\n  {unit} AS unit\n")
        rows = self.sql_rows(plugin, {"username": "admin", "unit": "Celsius"})
        self.assertEqual(rows, [{"username": "admin", "unit": "Celsius"}])

    def test_sql_tool_call_invalid_json_string(self):
        """Test that a malformed JSON string of arguments raises."""
        with self.assertRaises(SmarterSqlPluginError):
            self.load_sql_plugin().tool_call_fetch_plugin_response("{not json")

    def test_sql_tool_call_invalid_args_type(self):
        """Test that arguments of an unsupported type raise."""
        with self.assertRaises(SmarterSqlPluginError):
            self.load_sql_plugin().tool_call_fetch_plugin_response(42)  # type: ignore[arg-type]

    def test_sql_tool_call_list_of_non_dicts(self):
        """Test that a list containing non-dict arguments raises."""
        with self.assertRaises(SmarterSqlPluginError):
            self.load_sql_plugin().tool_call_fetch_plugin_response(["username", "admin"])

    def test_sql_tool_call_no_plugin_data(self):
        """Test that a tool call without plugin data raises."""
        plugin = self.load_sql_plugin()
        with mock.patch.object(SqlPlugin, "plugin_data", new_callable=mock.PropertyMock, return_value=None):
            with self.assertRaises(SmarterSqlPluginError):
                plugin.tool_call_fetch_plugin_response({"username": "admin"})

    def test_sql_tool_call_invalid_connection(self):
        """Test that a tool call with an invalid connection raises."""
        plugin = self.load_sql_plugin()
        plugin_data = SimpleNamespace(connection=None, sql_query=SQL_QUERY, limit=10)
        with mock.patch.object(SqlPlugin, "plugin_data", new_callable=mock.PropertyMock, return_value=plugin_data):
            with self.assertRaises(SmarterSqlPluginError):
                plugin.tool_call_fetch_plugin_response({"username": "admin"})

    def test_sql_tool_call_query_not_a_string(self):
        """Test that a tool call with a non-string query raises."""
        plugin = self.load_sql_plugin()
        plugin_data = SimpleNamespace(connection=self.sql_connection, sql_query=None, limit=10)
        with mock.patch.object(SqlPlugin, "plugin_data", new_callable=mock.PropertyMock, return_value=plugin_data):
            with self.assertRaises(SmarterSqlPluginError):
                plugin.tool_call_fetch_plugin_response({"username": "admin"})

    # =========================================================================
    # SqlPlugin: tool calls, query execution and caching
    # =========================================================================
    def test_sql_tool_call_sends_final_sql(self):
        """Test the exact SQL sent to the connection."""
        with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
            self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin", "unit": None})
        execute_query.assert_called_once()
        self.assertEqual(execute_query.call_args.kwargs["sql"], "SELECT 'admin' AS username, NULL AS unit;")

    def test_sql_tool_call_limit(self):
        """Test that the plugin limit is passed to the connection."""
        with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
            self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"})
        self.assertEqual(execute_query.call_args.kwargs["limit"], self.sql_plugin_yaml["spec"]["sqlData"]["limit"])

    def test_sql_tool_call_limit_is_capped(self):
        """Test that the plugin limit is capped at MAX_SQL_QUERY_LENGTH."""
        plugin = self.load_sql_plugin()
        plugin.plugin_data.limit = MAX_SQL_QUERY_LENGTH * 10  # type: ignore[union-attr]
        with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
            plugin.tool_call_fetch_plugin_response({"username": "admin"})
        self.assertEqual(execute_query.call_args.kwargs["limit"], MAX_SQL_QUERY_LENGTH)

    def test_sql_tool_call_no_limit_uses_max(self):
        """Test that a plugin without a limit uses MAX_SQL_QUERY_LENGTH."""
        plugin = self.load_sql_plugin()
        plugin.plugin_data.limit = None  # type: ignore[union-attr]
        with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
            plugin.tool_call_fetch_plugin_response({"username": "admin"})
        self.assertEqual(execute_query.call_args.kwargs["limit"], MAX_SQL_QUERY_LENGTH)

    def test_sql_tool_call_result_is_cached(self):
        """Test that identical tool calls are served from the cache."""
        with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
            first = self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"})
            second = self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"})
        self.assertEqual(first, second)
        execute_query.assert_called_once()

    def test_sql_tool_call_different_args_are_not_cached_together(self):
        """Test that tool calls with different arguments are cached separately."""
        with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
            self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"})
            self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "other"})
        self.assertEqual(execute_query.call_count, 2)

    def test_sql_tool_call_cache_is_per_connection(self):
        """Test that identical queries against different connections are cached separately."""
        other = self.new_sql_plugin("sql_other_connection", connection=SQL_CONNECTION_NAME_2)

        # pylint: disable=unused-argument
        def execute_query(connection, sql, limit):
            return json.dumps([{"connection": connection.name}])

        with mock.patch.object(SqlConnection, "execute_query", autospec=True, side_effect=execute_query):
            first = self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"})
            second = other.tool_call_fetch_plugin_response({"username": "admin"})
        self.assertEqual(json.loads(first), [{"connection": SQL_CONNECTION_NAME}])  # type: ignore[arg-type]
        self.assertEqual(json.loads(second), [{"connection": SQL_CONNECTION_NAME_2}])  # type: ignore[arg-type]

    def test_sql_tool_call_cache_is_per_limit(self):
        """Test that identical queries with different limits are cached separately."""
        with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
            self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"})
            plugin = self.load_sql_plugin()
            plugin.plugin_data.limit = 3  # type: ignore[union-attr]
            plugin.tool_call_fetch_plugin_response({"username": "admin"})
        self.assertEqual(execute_query.call_count, 2)

    def test_sql_tool_call_failure_returns_empty_string(self):
        """Test that a failed query returns an empty string."""
        with mock.patch.object(SqlConnection, "execute_query", return_value=False):
            self.assertEqual(self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"}), "")

    def test_sql_tool_call_failure_is_not_cached(self):
        """Test that a failed query is retried on the next tool call."""
        with mock.patch.object(SqlConnection, "execute_query", return_value=False):
            self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"})
        with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
            retval = self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"})
        execute_query.assert_called_once()
        self.assertEqual(retval, '[{"a": 1}]')

    def test_sql_tool_call_invalid_query_returns_empty_string(self):
        """
        Test that a query rejected by the remote database returns an empty string.

        SqlConnection.execute_query() catches the DatabaseError and returns False,
        which the plugin answers with an empty string.
        """
        plugin = self.new_sql_plugin("sql_invalid_query", sql_query="SELEKT {username} AS username, {unit} AS unit;")
        self.assertEqual(plugin.tool_call_fetch_plugin_response({"username": "admin"}), "")

    def test_sql_tool_call_invalid_query_is_not_cached(self):
        """Test that a query rejected by the remote database is not cached."""
        plugin = self.new_sql_plugin(
            "sql_invalid_query_cache", sql_query="SELEKT {username} AS username, {unit} AS unit;"
        )
        self.assertEqual(plugin.tool_call_fetch_plugin_response({"username": "admin"}), "")
        with mock.patch.object(SqlConnection, "execute_query", return_value='[{"a": 1}]') as execute_query:
            plugin.tool_call_fetch_plugin_response({"username": "admin"})
        execute_query.assert_called_once()

    def test_sql_tool_call_empty_result_returns_empty_string(self):
        """Test that an empty result returns an empty string."""
        for empty in ("", None, [], {}):
            cache.clear()
            with mock.patch.object(SqlConnection, "execute_query", return_value=empty):
                self.assertEqual(
                    self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"}),
                    "",
                    f"result={empty!r}",
                )

    def test_sql_tool_call_unexpected_result_type(self):
        """Test that an unexpected result type raises."""
        with mock.patch.object(SqlConnection, "execute_query", return_value=42):
            with self.assertRaises(SmarterSqlPluginError):
                self.load_sql_plugin().tool_call_fetch_plugin_response({"username": "admin"})
