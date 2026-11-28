"""
Test the query building and the field validation of PluginDataApi and PluginDataSql, and that PluginDataApi makes no request.

These methods don't touch the database, so the tests use unsaved instances, and patch the SQL connection.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.connection.models import ApiConnection
from smarter.apps.llmtool.models import PluginDataApi, PluginDataSql
from smarter.common.exceptions import SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase

PARAMETERS = {
    "type": "object",
    "properties": {"city": {"type": "string", "description": "The city."}},
    "required": ["city"],
}


class TestPluginDataApi(SmarterTestBase):
    """Test PluginDataApi without a database."""

    def plugin_data(self, **kwargs) -> PluginDataApi:
        connection = ApiConnection(name="test_connection", base_url="https://api.example.com", timeout=5)
        fields = {"endpoint": "/v1/weather/", "parameters": PARAMETERS, **kwargs}
        return PluginDataApi(connection=connection, **fields)

    def test_url_and_data(self):
        plugin_data = self.plugin_data(headers=[{"name": "Accept", "value": "application/json"}], body={"a": 1})
        self.assertEqual(plugin_data.url, "https://api.example.com/v1/weather/")
        data = plugin_data.data()
        self.assertEqual(data["endpoint"], "/v1/weather/")
        self.assertEqual(data["body"], {"a": 1})
        self.assertEqual(data["parameters"], PARAMETERS)

    def test_makes_no_request_of_its_own(self):
        """The model makes no request: an ApiPlugin's data comes from its tool call, through the tool runner (#1082)."""
        plugin_data = self.plugin_data(test_values=[{"name": "city", "value": "Paris"}])
        with self.assertRaises(NotImplementedError):
            plugin_data.sanitized_return_data({"city": "Paris"})
        for name in ("prepare_request", "execute_request", "test"):
            with self.subTest(method=name):
                self.assertFalse(hasattr(plugin_data, name))

    def test_validate_endpoint(self):
        self.plugin_data().validate_endpoint()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(endpoint="not a valid endpoint!").validate_endpoint()

    def test_validate_url_params(self):
        # a None value is valid: validation returns without raising.
        self.plugin_data(url_params=None).validate_url_params()
        self.plugin_data(url_params=[{"key": "units", "value": "metric"}]).validate_url_params()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(url_params={"units": "metric"}).validate_url_params()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(url_params=[{"units": "metric"}]).validate_url_params()

    def test_validate_headers(self):
        # a None value is valid: validation returns without raising.
        self.plugin_data(headers=None).validate_headers()
        self.plugin_data(headers=[{"name": "Accept", "value": "application/json"}]).validate_headers()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(headers={"Accept": "application/json"}).validate_headers()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(headers=[{"Accept": "application/json"}]).validate_headers()

    def test_validate_body(self):
        # a None value is valid: validation returns without raising.
        self.plugin_data(body=None).validate_body()
        self.plugin_data(body={"a": 1}).validate_body()
        self.plugin_data(body=[1, 2]).validate_body()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(body="a string").validate_body()

    def test_validate_test_values(self):
        # a None value is valid: validation returns without raising.
        self.plugin_data(test_values=None).validate_test_values()
        self.plugin_data(test_values=[{"name": "city", "value": "Paris"}]).validate_test_values()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(test_values={"city": "Paris"}).validate_test_values()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(test_values=[{"city": "Paris"}]).validate_test_values()

    def test_validate_all_placeholders_in_parameters(self):
        self.plugin_data(endpoint="v1/weather/{city}/").validate_all_placeholders_in_parameters()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(endpoint="v1/weather/{country}/").validate_all_placeholders_in_parameters()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(endpoint="v1/weather/{city}/", parameters=None).validate_all_placeholders_in_parameters()


class TestPluginDataSql(SmarterTestBase):
    """Test PluginDataSql without a database."""

    def plugin_data(self, **kwargs) -> PluginDataSql:
        fields = {
            "sql_query": "SELECT * FROM weather WHERE city = '{city}' <units>AND units = '{units}'</units>",
            "parameters": PARAMETERS,
            **kwargs,
        }
        return PluginDataSql(**fields)

    def test_prepare_sql(self):
        """Test that placeholders are replaced, unused tag pairs removed, and the limit appended."""
        plugin_data = self.plugin_data(limit=10)
        self.assertEqual(
            plugin_data.prepare_sql({"city": "Paris", "units": "metric"}),
            "SELECT * FROM weather WHERE city = 'Paris' AND units = 'metric' LIMIT 10;",
        )
        self.assertEqual(
            plugin_data.prepare_sql({"city": "Paris"}),
            "SELECT * FROM weather WHERE city = 'Paris' LIMIT 10;",
        )
        self.assertEqual(self.plugin_data().prepare_sql(None), "SELECT * FROM weather WHERE city = '{city}' ;")

    def test_data(self):
        data = self.plugin_data().data({"city": "Paris"})
        self.assertEqual(data["parameters"], PARAMETERS)
        self.assertIn("city = 'Paris'", data["sql_query"])

    def test_are_test_values_pydantic(self):
        self.assertTrue(self.plugin_data(test_values=[{"name": "city", "value": "Paris"}]).are_test_values_pydantic())
        self.assertFalse(self.plugin_data(test_values=[{"city": "Paris"}]).are_test_values_pydantic())
        self.assertFalse(self.plugin_data(test_values={"city": "Paris"}).are_test_values_pydantic())

    def test_validate_test_values(self):
        # a None value is valid: validation returns without raising.
        self.plugin_data(test_values=None).validate_test_values()
        self.plugin_data(test_values=[{"name": "city", "value": "Paris"}]).validate_test_values()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(test_values={"city": "Paris"}).validate_test_values()
        with self.assertRaises(SmarterValueError):
            self.plugin_data(test_values=[{"city": "Paris"}]).validate_test_values()

    def test_execute_query(self):
        """Test that the prepared sql and the limit are passed to the connection."""
        plugin_data = self.plugin_data(limit=5)
        connection = MagicMock()
        connection.execute_query.return_value = "[]"
        with patch.object(PluginDataSql, "connection", new=connection):
            self.assertEqual(plugin_data.sanitized_return_data({"city": "Paris"}), "[]")
        sql, limit = connection.execute_query.call_args.args
        self.assertIn("city = 'Paris'", sql)
        self.assertEqual(limit, 5)
