# pylint: disable=too-many-lines,protected-access
"""
Unit tests for :py:class:`smarter.apps.plugin.plugin.base.PluginBase`, exercised through its.

SqlPlugin and ApiPlugin subclasses, since PluginBase is abstract.
"""

import copy
from unittest import mock

from django.db.models.query import QuerySet

from smarter.apps.connection.models import ApiConnection, SqlConnection
from smarter.apps.plugin.manifest.models.api_plugin.const import (
    MANIFEST_KIND as API_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.manifest.models.sql_plugin.const import (
    MANIFEST_KIND as SQL_MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.models import (
    PluginDataApi,
    PluginDataSql,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.apps.plugin.plugin.api import ApiPlugin, SmarterApiPluginError
from smarter.apps.plugin.plugin.base import PluginBase, SmarterPluginError
from smarter.apps.plugin.plugin.sql import SmarterSqlPluginError, SqlPlugin
from smarter.apps.plugin.serializers import (
    PluginMetaSerializer,
    PluginPromptSerializer,
    PluginSelectorSerializer,
)
from smarter.apps.plugin.signals import (
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_deleting,
    plugin_ready,
    plugin_selected,
    plugin_updated,
)
from smarter.apps.provider.services.text_completion.const import OpenAIMessageKeys
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib import json
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.openai.enum import OpenAIToolCall, OpenAIToolTypes

from .base_classes import (
    API_CONNECTION_NAME,
    API_PLUGIN_NAME,
    SQL_CONNECTION_NAME,
    SQL_PLUGIN_NAME,
    SQL_QUERY,
    PluginTestBase,
    capture_signal,
)


# pylint: disable=too-many-public-methods
class TestPluginBase(PluginTestBase):
    """Test PluginBase, using both the shared SqlPlugin and ApiPlugin fixtures."""

    # =========================================================================
    # fixtures
    # =========================================================================
    def test_000_fixtures(self):
        """Test the class fixtures themselves, lest we get ahead of ourselves."""
        self.assertTrue(self.ready)
        self.assertIsInstance(self.api_connection, ApiConnection)
        self.assertIsInstance(self.api_connection_2, ApiConnection)
        self.assertIsInstance(self.sql_connection, SqlConnection)
        self.assertIsInstance(self.sql_connection_2, SqlConnection)
        self.assertIsInstance(self.sql_plugin, SqlPlugin)
        self.assertIsInstance(self.api_plugin, ApiPlugin)
        self.assertTrue(self.sql_plugin.ready)
        self.assertTrue(self.api_plugin.ready)

    def test_001_fixture_secrets_do_not_collide(self):
        """Test that the Api and Sql connection secrets are distinct records with their own values."""
        self.assertNotEqual(self.api_secret.pk, self.sql_secret.pk)
        self.assertEqual(self.api_secret.get_secret(), self.api_key)
        self.assertEqual(self.api_connection.api_key.get_secret(), self.api_key)  # type: ignore[union-attr]
        self.assertEqual(self.sql_connection.password.get_secret(), "smarter")  # type: ignore[union-attr]

    def test_002_fixture_connections_belong_to_account(self):
        """Test that all connections belong to the test account."""
        for connection in (self.api_connection, self.api_connection_2, self.sql_connection, self.sql_connection_2):
            self.assertEqual(connection.user_profile.account, self.account)  # type: ignore[union-attr]

    def test_003_fixture_plugins_persisted(self):
        """Test that the shared plugins exist in the database."""
        self.assertTrue(PluginMeta.objects.filter(id=self.sql_plugin.id, name=SQL_PLUGIN_NAME).exists())
        self.assertTrue(PluginMeta.objects.filter(id=self.api_plugin.id, name=API_PLUGIN_NAME).exists())
        self.assertTrue(PluginDataSql.objects.filter(plugin_id=self.sql_plugin.id).exists())
        self.assertTrue(PluginDataApi.objects.filter(plugin_id=self.api_plugin.id).exists())

    # =========================================================================
    # PluginBase: class structure
    # =========================================================================
    def test_base_is_abstract(self):
        """Test that PluginBase cannot be instantiated."""
        with self.assertRaises(TypeError):
            PluginBase()  # type: ignore[abstract]  # pylint: disable=abstract-class-instantiated

    def test_base_example_manifest_not_implemented(self):
        """Test that PluginBase.example_manifest() must be implemented by subclasses."""
        with self.assertRaises(NotImplementedError):
            PluginBase.example_manifest()

    def test_base_subclasses(self):
        """Test that SqlPlugin and ApiPlugin are PluginBase subclasses."""
        self.assertTrue(issubclass(SqlPlugin, PluginBase))
        self.assertTrue(issubclass(ApiPlugin, PluginBase))

    def test_base_errors_are_plugin_errors(self):
        """Test that the plugin-specific errors derive from SmarterPluginError."""
        self.assertTrue(issubclass(SmarterSqlPluginError, SmarterPluginError))
        self.assertTrue(issubclass(SmarterApiPluginError, SmarterPluginError))

    # =========================================================================
    # PluginBase: initialization
    # =========================================================================
    def test_base_init_by_plugin_id(self):
        """Test initializing a plugin from its PluginMeta id."""
        plugin = SqlPlugin(plugin_id=self.sql_plugin.id, user_profile=self.user_profile)
        self.assertTrue(plugin.ready)
        self.assertEqual(plugin.id, self.sql_plugin.id)
        self.assertEqual(plugin.name, SQL_PLUGIN_NAME)

    def test_base_init_by_plugin_meta(self):
        """Test initializing a plugin from a PluginMeta instance."""
        plugin_meta = PluginMeta.objects.get(id=self.api_plugin.id)
        plugin = ApiPlugin(plugin_meta=plugin_meta, user_profile=self.user_profile)
        self.assertTrue(plugin.ready)
        self.assertEqual(plugin.id, plugin_meta.id)

    def test_base_init_by_name(self):
        """Test initializing a plugin from its name."""
        plugin = SqlPlugin(name=SQL_PLUGIN_NAME, user_profile=self.user_profile)
        self.assertTrue(plugin.ready)
        self.assertEqual(plugin.id, self.sql_plugin.id)

    def test_base_init_by_positional_user_profile(self):
        """Test that a UserProfile passed as a positional argument is recognized."""
        plugin = SqlPlugin(self.user_profile, plugin_id=self.sql_plugin.id)
        self.assertEqual(plugin.user_profile, self.user_profile)
        self.assertTrue(plugin.ready)

    def test_base_init_by_plugin_id_requires_user_profile(self):
        """Test that initializing by plugin id without a UserProfile raises."""
        with self.assertRaises(SmarterPluginError):
            SqlPlugin(plugin_id=self.sql_plugin.id)

    def test_base_init_by_nonexistent_plugin_id(self):
        """Test that initializing by a nonexistent plugin id raises."""
        with self.assertRaises(SmarterPluginError):
            SqlPlugin(plugin_id=999999999, user_profile=self.user_profile)

    def test_base_init_manifest_wrong_type(self):
        """Test that a manifest of the wrong Pydantic type raises TypeError."""
        with self.assertRaises(TypeError):
            SqlPlugin(manifest=self.api_manifest("wrong_type"), user_profile=self.user_profile)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            ApiPlugin(manifest=self.sql_manifest("wrong_type"), user_profile=self.user_profile)  # type: ignore[arg-type]

    def test_base_init_from_data_dict(self):
        """Test initializing a plugin from a manifest dict."""
        name = "sql_from_data_dict"
        self.addCleanup(self.delete_plugin_by_name, name)
        plugin = SqlPlugin(data=self.sql_manifest_dict(name), user_profile=self.user_profile)
        self.assertTrue(plugin.ready)
        self.assertEqual(plugin.name, name)

    def test_base_init_from_data_json_string(self):
        """Test initializing a plugin from a manifest JSON string."""
        name = "api_from_data_json"
        self.addCleanup(self.delete_plugin_by_name, name)
        plugin = ApiPlugin(data=json.dumps(self.api_manifest_dict(name)), user_profile=self.user_profile)
        self.assertTrue(plugin.ready)
        self.assertEqual(plugin.name, name)

    def test_base_init_from_data_wrong_kind(self):
        """Test that manifest data of the wrong kind raises SAMValidationError."""
        with self.assertRaises(SAMValidationError):
            SqlPlugin(data=self.api_manifest_dict("wrong_kind"), user_profile=self.user_profile)

    def test_base_init_without_user_profile_is_not_ready(self):
        """Test that a plugin without a UserProfile is not ready."""
        plugin = SqlPlugin()
        self.assertFalse(plugin.ready)
        self.assertFalse(bool(plugin))
        self.assertIsNone(plugin.id)
        self.assertIsNone(plugin.name)

    def test_base_init_selected_flag(self):
        """Test that the selected constructor flag is honored."""
        plugin = SqlPlugin(plugin_id=self.sql_plugin.id, user_profile=self.user_profile, selected=True)
        self.assertTrue(plugin.selected(user=self.admin_user, input_text="xyzzy quux"))

    def test_base_init_api_version(self):
        """Test that the api_version constructor argument is honored."""
        plugin = SqlPlugin(plugin_id=self.sql_plugin.id, user_profile=self.user_profile, api_version="smarter.sh/v1")
        self.assertEqual(plugin.api_version, "smarter.sh/v1")

    # =========================================================================
    # PluginBase: dunder methods
    # =========================================================================
    def test_base_str_and_repr(self):
        """Test that __str__ and __repr__ include the name and kind."""
        for plugin in (self.sql_plugin, self.api_plugin):
            self.assertIn(str(plugin.name), str(plugin))
            self.assertIn(plugin.kind, str(plugin))
            self.assertEqual(str(plugin), repr(plugin))

    def test_base_bool(self):
        """Test that a ready plugin is truthy."""
        self.assertTrue(bool(self.sql_plugin))
        self.assertTrue(bool(self.api_plugin))

    def test_base_eq_same_plugin(self):
        """Test that two instances of the same plugin are equal."""
        self.assertEqual(self.load_sql_plugin(), self.load_sql_plugin())
        self.assertEqual(self.sql_plugin, self.load_sql_plugin())

    def test_base_eq_different_plugins(self):
        """Test that different plugins are not equal."""
        self.assertNotEqual(self.sql_plugin, self.api_plugin)

    def test_base_eq_other_type(self):
        """Test that a plugin is not equal to a non-plugin."""
        self.assertNotEqual(self.sql_plugin, "not a plugin")
        self.assertNotEqual(self.sql_plugin, None)

    def test_base_hash(self):
        """Test that equal plugins hash identically and deduplicate in a set."""
        plugin_a = self.load_sql_plugin()
        plugin_b = self.load_sql_plugin()
        self.assertEqual(hash(plugin_a), hash(plugin_b))
        self.assertEqual(len({plugin_a, plugin_b, self.api_plugin}), 2)

    def test_base_ordering(self):
        """Test that the rich comparison operators are mutually consistent."""
        low, high = sorted([self.sql_plugin, self.api_plugin])
        self.assertTrue(low < high)
        self.assertTrue(low <= high)
        self.assertTrue(high > low)
        self.assertTrue(high >= low)
        self.assertFalse(high < low)
        self.assertFalse(low > high)

    def test_base_ordering_equal_plugins(self):
        """Test the comparison operators on two instances of the same plugin."""
        plugin_a = self.load_sql_plugin()
        plugin_b = self.load_sql_plugin()
        self.assertFalse(plugin_a < plugin_b)
        self.assertTrue(plugin_a <= plugin_b)
        self.assertFalse(plugin_a > plugin_b)
        self.assertTrue(plugin_a >= plugin_b)

    def test_base_ordering_other_type(self):
        """Test that ordering against a non-plugin raises TypeError."""
        with self.assertRaises(TypeError):
            _ = self.sql_plugin < 1  # type: ignore[operator]
        with self.assertRaises(TypeError):
            _ = self.sql_plugin <= 1  # type: ignore[operator]
        with self.assertRaises(TypeError):
            _ = self.sql_plugin > 1  # type: ignore[operator]
        with self.assertRaises(TypeError):
            _ = self.sql_plugin >= 1  # type: ignore[operator]

    # =========================================================================
    # PluginBase: properties
    # =========================================================================
    def test_base_kind(self):
        """Test the kind of each plugin."""
        self.assertEqual(self.sql_plugin.kind, SQL_MANIFEST_KIND)
        self.assertEqual(self.api_plugin.kind, API_MANIFEST_KIND)

    def test_base_metadata_class(self):
        """Test that metadata_class reflects the PluginMeta plugin_class."""
        self.assertEqual(self.load_sql_plugin().metadata_class, "sql")
        self.assertEqual(self.load_api_plugin().metadata_class, "api")

    def test_base_metadata_class_not_ready(self):
        """Test that metadata_class is None without a PluginMeta."""
        self.assertIsNone(SqlPlugin().metadata_class)

    def test_base_formatted_pluginbase_class_name(self):
        """Test that the formatted class name includes the concrete class name."""
        self.assertIn("SqlPlugin", self.sql_plugin.formatted_pluginbase_class_name)
        self.assertIn("ApiPlugin", self.api_plugin.formatted_pluginbase_class_name)

    def test_base_params(self):
        """Test the params property and its setter."""
        plugin = self.load_sql_plugin()
        self.assertIsNone(plugin.params)
        plugin.params = {"username": "admin"}
        self.assertEqual(plugin.params, {"username": "admin"})

    def test_base_params_invalid(self):
        """Test that params must be a dict."""
        plugin = self.load_sql_plugin()
        with self.assertRaises(SmarterValueError):
            plugin.params = ["not", "a", "dict"]  # type: ignore[assignment]

    def test_base_api_version_valid(self):
        """Test that the api_version setter accepts compatible versions."""
        plugin = self.load_sql_plugin()
        plugin.api_version = "smarter.sh/v1"
        self.assertEqual(plugin.api_version, "smarter.sh/v1")

    def test_base_api_version_invalid(self):
        """Test that the api_version setter rejects incompatible versions."""
        plugin = self.load_sql_plugin()
        with self.assertRaises(SAMValidationError):
            plugin.api_version = "smarter.sh/v99"

    def test_base_id(self):
        """Test that id matches the PluginMeta id."""
        plugin = self.load_api_plugin()
        self.assertEqual(plugin.id, plugin.plugin_meta.id)  # type: ignore[union-attr]

    def test_base_name(self):
        """Test that name matches the PluginMeta name."""
        self.assertEqual(self.load_sql_plugin().name, SQL_PLUGIN_NAME)
        self.assertEqual(self.load_api_plugin().name, API_PLUGIN_NAME)

    def test_base_plugin_meta(self):
        """Test the PluginMeta model."""
        plugin_meta = self.load_sql_plugin().plugin_meta
        self.assertIsInstance(plugin_meta, PluginMeta)
        self.assertEqual(plugin_meta.name, SQL_PLUGIN_NAME)  # type: ignore[union-attr]
        self.assertEqual(plugin_meta.plugin_class, "sql")  # type: ignore[union-attr]
        self.assertEqual(plugin_meta.user_profile, self.user_profile)  # type: ignore[union-attr]
        self.assertEqual(plugin_meta.version, self.sql_plugin_yaml["metadata"]["version"])  # type: ignore[union-attr]

    def test_base_plugin_meta_tags(self):
        """Test that manifest tags are persisted."""
        plugin_meta = self.load_sql_plugin().plugin_meta
        tags = {tag.name for tag in plugin_meta.tags.all()}  # type: ignore[union-attr]
        self.assertSetEqual(tags, set(self.sql_plugin_yaml["metadata"]["tags"]))

    def test_base_plugin_meta_serializer(self):
        """Test the PluginMeta serializer."""
        serializer = self.load_sql_plugin().plugin_meta_serializer
        self.assertIsInstance(serializer, PluginMetaSerializer)
        self.assertEqual(serializer.data["name"], SQL_PLUGIN_NAME)  # type: ignore[union-attr]

    def test_base_plugin_meta_django_model(self):
        """Test the PluginMeta Django model dict constructed from the manifest."""
        model = self.sql_plugin.plugin_meta_django_model
        self.assertIsInstance(model, dict)
        self.assertEqual(model["name"], SQL_PLUGIN_NAME)  # type: ignore[index]
        self.assertEqual(model["plugin_class"], "sql")  # type: ignore[index]
        self.assertEqual(model["user_profile"], self.user_profile)  # type: ignore[index]

    def test_base_plugin_meta_django_model_without_manifest(self):
        """Test that the PluginMeta Django model dict requires a manifest."""
        self.assertIsNone(self.load_sql_plugin().plugin_meta_django_model)

    def test_base_plugin_selector_search_terms(self):
        """Test the PluginSelector of a search_terms plugin."""
        selector = self.load_sql_plugin().plugin_selector
        self.assertIsInstance(selector, PluginSelector)
        self.assertEqual(selector.directive, "search_terms")  # type: ignore[union-attr]
        self.assertEqual(
            selector.search_terms, self.sql_plugin_yaml["spec"]["selector"]["searchTerms"]  # type: ignore[union-attr]
        )

    def test_base_plugin_selector_always(self):
        """Test the PluginSelector of an always plugin."""
        selector = self.load_api_plugin().plugin_selector
        self.assertIsInstance(selector, PluginSelector)
        self.assertEqual(selector.directive, "always")  # type: ignore[union-attr]

    def test_base_plugin_selector_serializer(self):
        """Test the PluginSelector serializer."""
        serializer = self.load_sql_plugin().plugin_selector_serializer
        self.assertIsInstance(serializer, PluginSelectorSerializer)
        self.assertEqual(serializer.data["directive"], "search_terms")  # type: ignore[union-attr]

    def test_base_plugin_selector_django_model(self):
        """Test the PluginSelector Django model dict constructed from the manifest."""
        model = self.sql_plugin.plugin_selector_django_model
        self.assertIsInstance(model, dict)
        self.assertEqual(model["directive"], "search_terms")  # type: ignore[index]

    def test_base_plugin_selector_django_model_without_manifest(self):
        """Test that the PluginSelector Django model dict requires a manifest."""
        self.assertIsNone(self.load_sql_plugin().plugin_selector_django_model)

    def test_base_plugin_selector_history(self):
        """Test that the selector history is a QuerySet."""
        self.assertIsInstance(self.load_sql_plugin().plugin_selector_history, QuerySet)

    def test_base_plugin_selector_not_ready(self):
        """Test that the selector is None without a PluginMeta."""
        self.assertIsNone(SqlPlugin().plugin_selector)

    def test_base_plugin_prompt(self):
        """Test the PluginPrompt model."""
        prompt = self.load_sql_plugin().plugin_prompt
        expected = self.sql_plugin_yaml["spec"]["prompt"]
        self.assertIsInstance(prompt, PluginPrompt)
        self.assertEqual(prompt.system_role.strip(), expected["systemRole"].strip())  # type: ignore[union-attr]
        self.assertEqual(prompt.model, expected["model"])  # type: ignore[union-attr]
        self.assertEqual(float(prompt.temperature), float(expected["temperature"]))  # type: ignore[union-attr]
        self.assertEqual(prompt.max_completion_tokens, expected["maxTokens"])  # type: ignore[union-attr]

    def test_base_plugin_prompt_serializer(self):
        """Test the PluginPrompt serializer."""
        serializer = self.load_api_plugin().plugin_prompt_serializer
        self.assertIsInstance(serializer, PluginPromptSerializer)
        self.assertEqual(serializer.data["model"], "gpt-6-luna")  # type: ignore[union-attr]

    def test_base_plugin_prompt_django_model(self):
        """Test the PluginPrompt Django model dict constructed from the manifest."""
        model = self.api_plugin.plugin_prompt_django_model
        self.assertIsInstance(model, dict)
        self.assertEqual(model["model"], "gpt-6-luna")  # type: ignore[index]
        self.assertEqual(model["max_completion_tokens"], 256)  # type: ignore[index]

    def test_base_plugin_prompt_django_model_without_manifest(self):
        """Test that the PluginPrompt Django model dict requires a manifest."""
        self.assertIsNone(self.load_api_plugin().plugin_prompt_django_model)

    def test_base_plugin_prompt_not_ready(self):
        """Test that the prompt is None without a PluginMeta."""
        self.assertIsNone(SqlPlugin().plugin_prompt)

    def test_base_function_calling_identifier(self):
        """Test the OpenAI function calling identifier format."""
        plugin = self.load_sql_plugin()
        expected = f"{smarter_settings.function_calling_identifier_prefix}_{str(plugin.id).zfill(10)}"
        self.assertEqual(plugin.function_calling_identifier, expected)

    def test_base_function_calling_identifier_unique(self):
        """Test that function calling identifiers are unique per plugin."""
        self.assertNotEqual(
            self.load_sql_plugin().function_calling_identifier, self.load_api_plugin().function_calling_identifier
        )

    def test_base_function_parameters_sql(self):
        """Test the OpenAI function parameters schema of the SqlPlugin."""
        parameters = self.load_sql_plugin().function_parameters
        self.assertEqual(parameters["type"], "object")  # type: ignore[index]
        self.assertFalse(parameters["additionalProperties"])  # type: ignore[index]
        self.assertSetEqual(set(parameters["properties"].keys()), {"username", "unit"})  # type: ignore[index]
        self.assertEqual(parameters["required"], ["username"])  # type: ignore[index]
        self.assertEqual(parameters["properties"]["unit"]["enum"], ["Celsius", "Fahrenheit"])  # type: ignore[index]
        self.assertEqual(parameters["properties"]["username"]["default"], "admin")  # type: ignore[index]

    def test_base_function_parameters_api(self):
        """Test the OpenAI function parameters schema of the ApiPlugin."""
        parameters = self.load_api_plugin().function_parameters
        self.assertSetEqual(set(parameters["properties"].keys()), {"kind", "source"})  # type: ignore[index]
        self.assertEqual(parameters["required"], ["kind"])  # type: ignore[index]
        self.assertEqual(parameters["properties"]["kind"]["enum"], ["list", "dict"])  # type: ignore[index]
        self.assertNotIn("default", parameters["properties"]["source"])  # type: ignore[index]

    def test_base_function_parameters_adds_required(self):
        """Test that function_parameters adds an empty required list when missing."""
        plugin = self.load_sql_plugin()
        plugin.plugin_data.parameters = {"type": "object", "properties": {}}  # type: ignore[union-attr]
        self.assertEqual(plugin.function_parameters["required"], [])  # type: ignore[index]

    def test_base_function_parameters_not_dict(self):
        """Test that function_parameters raises when parameters is not a dict."""
        plugin = self.load_sql_plugin()
        plugin.plugin_data.parameters = ["not", "a", "dict"]  # type: ignore[union-attr]
        with self.assertRaises(SmarterConfigurationError):
            _ = plugin.function_parameters

    def test_base_function_parameters_no_plugin_data(self):
        """Test that function_parameters raises without plugin data."""
        plugin = self.load_sql_plugin()
        with mock.patch.object(SqlPlugin, "plugin_data", new_callable=mock.PropertyMock, return_value=None):
            with self.assertRaises(SmarterPluginError):
                _ = plugin.function_parameters

    def test_base_custom_tool(self):
        """Test the OpenAI custom tool definition."""
        for plugin in (self.load_sql_plugin(), self.load_api_plugin()):
            tool = plugin.custom_tool
            function = tool[OpenAIToolCall.FUNCTION.value]
            self.assertEqual(tool[OpenAIToolCall.TYPE.value], OpenAIToolTypes.FUNCTION.value)
            self.assertEqual(function[OpenAIToolCall.NAME.value], plugin.function_calling_identifier)
            self.assertEqual(function[OpenAIToolCall.DESCRIPTION.value], plugin.plugin_data.description)  # type: ignore[union-attr]
            self.assertEqual(function[OpenAIToolCall.PARAMETERS.value], plugin.function_parameters)

    def test_base_custom_tool_is_json_serializable(self):
        """Test that the custom tool can be sent to the OpenAI api as JSON."""
        tool = self.load_api_plugin().custom_tool
        self.assertEqual(json.loads(json.dumps(tool)), tool)

    def test_base_custom_tool_parameters_not_dict(self):
        """Test that custom_tool raises when parameters is not a dict."""
        plugin = self.load_sql_plugin()
        plugin.plugin_data.parameters = "not a dict"  # type: ignore[union-attr]
        with self.assertRaises(SmarterConfigurationError):
            _ = plugin.custom_tool

    def test_base_data(self):
        """Test that data is the JSON representation of a ready plugin."""
        plugin = self.load_sql_plugin()
        self.assertEqual(plugin.data, plugin.to_json())

    def test_base_yaml(self):
        """Test that yaml is a YAML representation of the plugin."""
        plugin = self.load_api_plugin()
        data = plugin.yaml_to_json(plugin.yaml)
        self.assertEqual(data["kind"], API_MANIFEST_KIND)
        self.assertEqual(data["metadata"]["name"], API_PLUGIN_NAME)

    def test_base_refresh(self):
        """Test that refresh reloads a ready plugin."""
        plugin = self.load_sql_plugin()
        plugin_id = plugin.id
        self.assertTrue(plugin.refresh())
        self.assertEqual(plugin.id, plugin_id)

    def test_base_reinitialize_plugin(self):
        """Test that reinitialize_plugin clears the cached Django models."""
        plugin = self.load_sql_plugin()
        _ = plugin.plugin_selector, plugin.plugin_prompt, plugin.plugin_meta_serializer
        plugin.reinitialize_plugin()
        self.assertIsNone(plugin._plugin_meta)
        self.assertIsNone(plugin._plugin_selector)
        self.assertIsNone(plugin._plugin_prompt)
        self.assertIsNone(plugin._plugin_data)
        self.assertIsNone(plugin._plugin_meta_serializer)

    def test_base_cache_invalidations(self):
        """Test that cache invalidation does not disturb a ready plugin."""
        plugin = self.load_api_plugin()
        plugin.cache_invalidations()
        self.assertEqual(self.load_api_plugin().id, plugin.id)

    # =========================================================================
    # PluginBase: not-ready behavior
    # =========================================================================
    def test_base_not_ready_data_is_none(self):
        """Test that data is None for a plugin that is not ready."""
        self.assertIsNone(SqlPlugin().data)

    def test_base_not_ready_yaml_raises(self):
        """Test that yaml raises for a plugin that is not ready."""
        with self.assertRaises(SmarterPluginError):
            _ = SqlPlugin().yaml

    def test_base_not_ready_function_calling_identifier_raises(self):
        """Test that function_calling_identifier raises for a plugin that is not ready."""
        with self.assertRaises(SmarterPluginError):
            _ = ApiPlugin().function_calling_identifier

    def test_base_not_ready_custom_tool_raises(self):
        """Test that custom_tool raises for a plugin that is not ready."""
        with self.assertRaises(SmarterPluginError):
            _ = ApiPlugin().custom_tool

    def test_base_not_ready_customize_prompt_raises(self):
        """Test that customize_prompt raises for a plugin that is not ready."""
        with self.assertRaises(SmarterPluginError):
            SqlPlugin().customize_prompt([{"role": "system", "content": "hi"}])

    def test_base_not_ready_selected_is_false(self):
        """Test that a plugin that is not ready is never selected."""
        self.assertFalse(SqlPlugin().selected(user=self.admin_user, input_text="admin"))

    def test_base_not_ready_refresh_is_false(self):
        """Test that refresh returns False for a plugin that is not ready."""
        self.assertFalse(SqlPlugin().refresh())

    def test_base_not_ready_save_is_false(self):
        """Test that save returns False for a plugin that is not ready."""
        self.assertFalse(SqlPlugin().save())

    def test_base_not_ready_delete_is_false(self):
        """Test that delete returns False for a plugin that is not ready."""
        self.assertFalse(SqlPlugin().delete())

    def test_base_not_ready_clone_is_false(self):
        """Test that clone returns False for a plugin that is not ready."""
        self.assertFalse(SqlPlugin().clone())

    def test_base_not_ready_to_json_is_none(self):
        """Test that to_json returns None for a plugin that is not ready."""
        self.assertIsNone(SqlPlugin().to_json())
        self.assertIsNone(ApiPlugin().to_json())

    def test_base_create_without_manifest_raises(self):
        """Test that create requires a manifest."""
        with self.assertRaises(SmarterPluginError):
            self.load_sql_plugin().create()

    def test_base_update_without_manifest_raises(self):
        """Test that update requires a manifest."""
        plugin = self.load_sql_plugin()
        with mock.patch.object(SqlPlugin, "manifest", new_callable=mock.PropertyMock, return_value=None):
            with self.assertRaises(SmarterPluginError):
                plugin.update()

    # =========================================================================
    # PluginBase: selection
    # =========================================================================
    def test_base_selected_always(self):
        """Test that an always plugin is selected regardless of input."""
        self.assertTrue(self.load_api_plugin().selected(user=self.admin_user, input_text="xyzzy quux"))

    def test_base_selected_always_without_input(self):
        """Test that an always plugin is selected without any input."""
        self.assertTrue(self.load_api_plugin().selected(user=self.admin_user))

    def test_base_selected_by_input_text(self):
        """Test that a search term in the input text selects the plugin."""
        self.assertTrue(
            self.load_sql_plugin().selected(user=self.admin_user, input_text="Tell me about the admin account.")
        )

    def test_base_not_selected_by_unrelated_input_text(self):
        """Test that unrelated input text does not select the plugin."""
        self.assertFalse(self.load_sql_plugin().selected(user=self.admin_user, input_text="xyzzy quux"))

    def test_base_not_selected_without_input(self):
        """Test that a search_terms plugin is not selected without any input."""
        self.assertFalse(self.load_sql_plugin().selected(user=self.admin_user))

    def test_base_selected_by_user_message(self):
        """Test that a search term in a user message selects the plugin."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me about the admin account."},
        ]
        self.assertTrue(self.load_sql_plugin().selected(user=self.admin_user, messages=messages))

    def test_base_selected_by_user_message_role_is_case_insensitive(self):
        """Test that message roles are matched case-insensitively."""
        messages = [{"role": "USER", "content": "Tell me about the admin account."}]
        self.assertTrue(self.load_sql_plugin().selected(user=self.admin_user, messages=messages))

    def test_base_not_selected_by_assistant_message(self):
        """Test that search terms in non-user messages are ignored."""
        messages = [
            {"role": "system", "content": "Tell me about the admin account."},
            {"role": "assistant", "content": "Tell me about the admin account."},
        ]
        self.assertFalse(self.load_sql_plugin().selected(user=self.admin_user, messages=messages))

    def test_base_selected_is_sticky(self):
        """Test that once selected, a plugin remains selected."""
        plugin = self.load_sql_plugin()
        self.assertTrue(plugin.selected(user=self.admin_user, input_text="Tell me about the admin account."))
        self.assertTrue(plugin.selected(user=self.admin_user, input_text="xyzzy quux"))

    def test_base_selected_sends_signal(self):
        """Test that selection by search term sends the plugin_selected signal."""
        with capture_signal(plugin_selected) as received:
            self.load_sql_plugin().selected(user=self.admin_user, input_text="Tell me about the admin account.")
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["input_text"], "Tell me about the admin account.")
        self.assertIn(received[0]["search_term"], self.sql_plugin_yaml["spec"]["selector"]["searchTerms"])

    def test_base_not_selected_sends_no_signal(self):
        """Test that no plugin_selected signal is sent when the plugin is not selected."""
        with capture_signal(plugin_selected) as received:
            self.load_sql_plugin().selected(user=self.admin_user, input_text="xyzzy quux")
        self.assertEqual(received, [])

    # =========================================================================
    # PluginBase: prompt customization
    # =========================================================================
    def test_base_customize_prompt(self):
        """Test that the plugin system role is appended to the system message."""
        plugin = self.load_sql_plugin()
        messages = [
            {OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY, "content": "Base role."},
            {OpenAIMessageKeys.MESSAGE_ROLE_KEY: "user", "content": "Hello"},
        ]
        customized = plugin.customize_prompt(messages)
        content = customized[0][OpenAIMessageKeys.MESSAGE_CONTENT_KEY]
        self.assertTrue(content.startswith("Base role.\n\nAnd also:\n"))
        self.assertTrue(content.endswith(plugin.plugin_prompt.system_role))  # type: ignore[union-attr]
        self.assertEqual(customized[1], messages[1])

    def test_base_customize_prompt_does_not_mutate_input(self):
        """Test that customize_prompt does not modify the messages it receives."""
        messages = [{OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY, "content": "Base role."}]
        original = copy.deepcopy(messages)
        self.load_sql_plugin().customize_prompt(messages)
        self.assertEqual(messages, original)

    def test_base_customize_prompt_only_first_system_message(self):
        """Test that only the first system message is customized."""
        messages = [
            {OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY, "content": "First."},
            {OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY, "content": "Second."},
        ]
        customized = self.load_sql_plugin().customize_prompt(messages)
        self.assertIn("And also:", customized[0]["content"])
        self.assertEqual(customized[1]["content"], "Second.")

    def test_base_customize_prompt_without_system_message(self):
        """Test that messages without a system message are returned unchanged."""
        messages = [{OpenAIMessageKeys.MESSAGE_ROLE_KEY: "user", "content": "Hello"}]
        self.assertEqual(self.load_sql_plugin().customize_prompt(messages), messages)

    def test_base_customize_prompt_empty_messages(self):
        """Test that customize_prompt rejects an empty messages list."""
        with self.assertRaises(SmarterValueError):
            self.load_sql_plugin().customize_prompt([])

    # =========================================================================
    # PluginBase: yaml and parameter helpers
    # =========================================================================
    def test_base_yaml_to_json(self):
        """Test converting a YAML string to a dict."""
        self.assertEqual(self.sql_plugin.yaml_to_json("a: 1\nb:\n  - x\n"), {"a": 1, "b": ["x"]})

    def test_base_yaml_to_json_invalid(self):
        """Test that invalid YAML raises SmarterPluginError."""
        with self.assertRaises(SmarterPluginError):
            self.sql_plugin.yaml_to_json("a: [unclosed")

    def test_base_is_valid_yaml(self):
        """Test YAML validation."""
        self.assertTrue(self.sql_plugin.is_valid_yaml("a: 1"))
        self.assertFalse(self.sql_plugin.is_valid_yaml("a: [unclosed"))

    def test_base_parameter_factory(self):
        """Test the parameter factory."""
        parameter = PluginBase.parameter_factory(
            name="city", data_type="string", description="A city.", required=True, default="Paris"
        )
        self.assertEqual(
            parameter,
            {"name": "city", "type": "string", "description": "A city.", "required": True, "default": "Paris"},
        )

    def test_base_parameter_factory_defaults(self):
        """Test the parameter factory default values."""
        parameter = PluginBase.parameter_factory(name="city", data_type="string", description="A city.")
        self.assertFalse(parameter["required"])
        self.assertIsNone(parameter["default"])
        self.assertNotIn("enum", parameter)

    def test_base_parameter_factory_enum(self):
        """Test the parameter factory with an enum."""
        parameter = PluginBase.parameter_factory(
            name="unit", data_type="string", description="A unit.", enum=["Celsius", "Fahrenheit"]
        )
        self.assertEqual(parameter["enum"], ["Celsius", "Fahrenheit"])

    def test_base_parameter_factory_enum_not_list(self):
        """Test that the parameter factory rejects a non-list enum."""
        with self.assertRaises(SmarterConfigurationError):
            PluginBase.parameter_factory(name="unit", data_type="string", description="A unit.", enum="Celsius")  # type: ignore[arg-type]

    def test_base_parameter_factory_is_valid_parameter(self):
        """Test that the parameter factory output is a valid manifest Parameter."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.plugin.manifest.models.common import Parameter

        parameter = PluginBase.parameter_factory(
            name="unit", data_type="string", description="A unit.", enum=["Celsius", "Fahrenheit"], default="Celsius"
        )
        self.assertEqual(Parameter(**parameter).name, "unit")

    def test_base_parameters_to_manifest(self):
        """Test converting OpenAI function calling parameters back to manifest parameters."""
        parameters = {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "A city.", "default": "Paris"},
                "unit": {"type": "string", "description": "A unit.", "enum": ["Celsius", "Fahrenheit"]},
            },
            "required": ["city"],
            "additionalProperties": False,
        }
        self.assertEqual(
            PluginBase.parameters_to_manifest(parameters),
            [
                {"name": "city", "type": "string", "description": "A city.", "required": True, "default": "Paris"},
                {
                    "name": "unit",
                    "type": "string",
                    "description": "A unit.",
                    "required": False,
                    "default": None,
                    "enum": ["Celsius", "Fahrenheit"],
                },
            ],
        )

    def test_base_parameters_to_manifest_empty(self):
        """Test that empty parameters convert to None."""
        for parameters in (None, {}, []):
            self.assertIsNone(PluginBase.parameters_to_manifest(parameters), f"parameters={parameters!r}")

    def test_base_parameters_to_manifest_no_properties(self):
        """Test that parameters without properties convert to an empty list."""
        self.assertEqual(PluginBase.parameters_to_manifest({"type": "object", "properties": {}}), [])

    def test_base_parameters_to_manifest_list_passthrough(self):
        """Test that parameters already in manifest format are returned unchanged."""
        parameters = [{"name": "city", "type": "string"}]
        self.assertIs(PluginBase.parameters_to_manifest(parameters), parameters)

    def test_base_parameters_to_manifest_without_required(self):
        """Test that parameters without a required list are all optional."""
        parameters = {"type": "object", "properties": {"city": {"type": "string"}}}
        self.assertFalse(PluginBase.parameters_to_manifest(parameters)[0]["required"])  # type: ignore[index]

    def test_base_parameters_round_trip(self):
        """Test that recasting manifest parameters and converting them back is lossless."""
        for plugin, original in (
            (self.load_sql_plugin(), self.sql_plugin_yaml["spec"]["sqlData"]["parameters"]),
            (self.load_api_plugin(), self.api_manifest_dict("x")["spec"]["apiData"]["parameters"]),
        ):
            converted = PluginBase.parameters_to_manifest(plugin.plugin_data.parameters)  # type: ignore[union-attr]
            for expected, actual in zip(original, converted):  # type: ignore[arg-type]
                self.assertEqual(actual["name"], expected["name"])
                self.assertEqual(actual["type"], expected["type"])
                self.assertEqual(actual["required"], expected.get("required", False))
                self.assertEqual(actual.get("enum"), expected.get("enum"))
                self.assertEqual(actual["default"], expected.get("default"))

    # =========================================================================
    # PluginBase: serialization
    # =========================================================================
    def test_base_to_json_structure(self):
        """Test the top-level structure of to_json()."""
        data = self.load_sql_plugin().to_json()
        self.assertSetEqual(set(data.keys()), {"apiVersion", "kind", "metadata", "spec", "status"})  # type: ignore[union-attr]
        self.assertEqual(data["apiVersion"], "smarter.sh/v1")  # type: ignore[index]
        self.assertEqual(data["kind"], SQL_MANIFEST_KIND)  # type: ignore[index]

    def test_base_to_json_spec(self):
        """Test the spec section of to_json()."""
        spec = self.load_sql_plugin().to_json()["spec"]  # type: ignore[index]
        self.assertEqual(spec["selector"]["directive"], "search_terms")
        self.assertEqual(spec["prompt"]["model"], self.sql_plugin_yaml["spec"]["prompt"]["model"])

    def test_base_to_json_status(self):
        """Test the status section of to_json()."""
        plugin = self.load_api_plugin()
        status = plugin.to_json()["status"]  # type: ignore[index]
        self.assertEqual(status["id"], plugin.id)
        self.assertEqual(status["accountNumber"], self.account.account_number)
        self.assertEqual(status["username"], self.admin_user.get_username())
        self.assertIsNotNone(status["created"])
        self.assertIsNotNone(status["updated"])
        self.assertEqual(status["recordLocator"], plugin.plugin_meta.record_locator)  # type: ignore[union-attr]
        self.assertEqual(status["modified"], status["updated"])

    def test_base_to_json_spec_connection(self):
        """Test that to_json exposes the connection as a top-level spec field, as in the manifest."""
        self.assertEqual(self.load_sql_plugin().to_json()["spec"]["connection"], SQL_CONNECTION_NAME)  # type: ignore[index]
        self.assertEqual(self.load_api_plugin().to_json()["spec"]["connection"], API_CONNECTION_NAME)  # type: ignore[index]

    def test_base_to_json_is_json_serializable(self):
        """Test that to_json() round trips through JSON."""
        for plugin in (self.load_sql_plugin(), self.load_api_plugin()):
            data = plugin.to_json()
            self.assertEqual(json.loads(json.dumps(data)), data)

    def test_base_to_json_invalid_version(self):
        """Test that to_json() rejects unsupported versions."""
        for plugin in (self.load_sql_plugin(), self.load_api_plugin()):
            with self.assertRaises(SmarterPluginError):
                plugin.to_json(version="v2")

    # =========================================================================
    # PluginBase: lifecycle
    # =========================================================================
    def test_base_create_sends_signals(self):
        """Test that creating a plugin sends plugin_created and plugin_ready."""
        with capture_signal(plugin_created) as created, capture_signal(plugin_ready) as ready:
            plugin = self.new_sql_plugin("sql_create_signals")
        self.assertTrue(plugin.ready)
        self.assertEqual(len(created), 1)
        self.assertGreaterEqual(len(ready), 1)

    def test_base_create_persists_all_models(self):
        """Test that creating a plugin persists meta, selector, prompt and data."""
        plugin = self.new_api_plugin("api_create_models")
        self.assertTrue(PluginMeta.objects.filter(id=plugin.id).exists())
        self.assertTrue(PluginSelector.objects.filter(plugin_id=plugin.id).exists())
        self.assertTrue(PluginPrompt.objects.filter(plugin_id=plugin.id).exists())
        self.assertTrue(PluginDataApi.objects.filter(plugin_id=plugin.id).exists())

    def test_base_create_existing_updates(self):
        """Test that creating a plugin that already exists updates it in place."""
        name = "sql_create_updates"
        plugin = self.new_sql_plugin(name)
        manifest = self.sql_manifest_dict(name)
        manifest["spec"]["prompt"]["temperature"] = 0.9
        manifest["spec"]["sqlData"]["limit"] = 7
        with capture_signal(plugin_updated) as updated, capture_signal(plugin_created) as created:
            updated_plugin = SqlPlugin(manifest=SAMSqlPlugin(**manifest), user_profile=self.user_profile)
        self.assertEqual(updated_plugin.id, plugin.id)
        self.assertGreaterEqual(len(updated), 1)
        self.assertEqual(created, [])
        self.assertAlmostEqual(float(PluginPrompt.objects.get(plugin_id=plugin.id).temperature), 0.9)
        self.assertEqual(PluginDataSql.objects.get(plugin_id=plugin.id).limit, 7)
        self.assertEqual(PluginMeta.objects.filter(user_profile__account=self.account, name=name).count(), 1)

    def test_base_update_is_not_served_from_a_stale_cache(self):
        """Test that a plugin loaded after an update sees the updated plugin data, not a cached copy."""
        sql_name = "sql_update_cache"
        sql_plugin = self.new_sql_plugin(sql_name)
        _ = SqlPlugin(plugin_id=sql_plugin.id, user_profile=self.user_profile).plugin_data  # populate the cache
        manifest = self.sql_manifest_dict(sql_name)
        manifest["spec"]["sqlData"]["limit"] = 7
        SqlPlugin(manifest=SAMSqlPlugin(**manifest), user_profile=self.user_profile)
        reloaded = SqlPlugin(plugin_id=sql_plugin.id, user_profile=self.user_profile)
        self.assertEqual(reloaded.plugin_data.limit, 7)  # type: ignore[union-attr]

        api_name = "api_update_cache"
        api_plugin = self.new_api_plugin(api_name)
        _ = ApiPlugin(plugin_id=api_plugin.id, user_profile=self.user_profile).plugin_data  # populate the cache
        manifest = self.api_manifest_dict(api_name)
        manifest["spec"]["apiData"]["endpoint"] = "/api/v1/tests/unauthenticated/{kind}/updated/"
        ApiPlugin(manifest=SAMApiPlugin(**manifest), user_profile=self.user_profile)
        reloaded_api = ApiPlugin(plugin_id=api_plugin.id, user_profile=self.user_profile)
        self.assertEqual(reloaded_api.plugin_data.endpoint, "/api/v1/tests/unauthenticated/{kind}/updated/")  # type: ignore[union-attr]

    def test_base_update_changes_selector(self):
        """Test that updating a plugin updates its selector."""
        name = "api_update_selector"
        plugin = self.new_api_plugin(name)
        manifest = self.api_manifest_dict(name)
        manifest["spec"]["selector"] = {"directive": "search_terms", "searchTerms": ["weather"]}
        ApiPlugin(manifest=SAMApiPlugin(**manifest), user_profile=self.user_profile)
        selector = PluginSelector.objects.get(plugin_id=plugin.id)
        self.assertEqual(selector.directive, "search_terms")
        self.assertEqual(selector.search_terms, ["weather"])

    def test_base_save(self):
        """Test that save persists a ready plugin and sends plugin_updated."""
        plugin = self.new_sql_plugin("sql_save")
        with capture_signal(plugin_updated) as updated:
            self.assertTrue(plugin.save())
        self.assertEqual(len(updated), 1)

    def test_base_delete(self):
        """Test that delete removes all models and sends signals."""
        plugin = self.new_sql_plugin("sql_delete")
        plugin_id = plugin.id
        with capture_signal(plugin_deleting) as deleting, capture_signal(plugin_deleted) as deleted:
            self.assertTrue(plugin.delete())
        self.assertEqual(len(deleting), 1)
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0]["plugin_name"], "sql_delete")
        self.assertFalse(PluginMeta.objects.filter(id=plugin_id).exists())
        self.assertFalse(PluginSelector.objects.filter(plugin_id=plugin_id).exists())
        self.assertFalse(PluginPrompt.objects.filter(plugin_id=plugin_id).exists())
        self.assertFalse(PluginDataSql.objects.filter(plugin_id=plugin_id).exists())

    def test_base_delete_clears_references(self):
        """Test that delete clears the plugin's cached Django models."""
        plugin = self.new_api_plugin("api_delete_refs")
        plugin.delete()
        self.assertIsNone(plugin._plugin_meta)
        self.assertIsNone(plugin._plugin_selector)
        self.assertIsNone(plugin._plugin_prompt)
        self.assertIsNone(plugin._plugin_data)

    def test_base_delete_does_not_delete_connection(self):
        """Test that deleting a plugin leaves its connection intact."""
        plugin = self.new_api_plugin("api_delete_keeps_connection")
        plugin.delete()
        self.assertTrue(ApiConnection.objects.filter(pk=self.api_connection.pk).exists())

    def test_base_clone_default_name(self):
        """Test cloning a plugin with a generated name."""
        name = "sql_clone_default"
        plugin = self.new_sql_plugin(name)
        with capture_signal(plugin_cloned) as cloned:
            clone_id = plugin.clone()
        self.addCleanup(self.delete_plugin_by_id, clone_id)
        self.assertEqual(len(cloned), 1)
        clone = PluginMeta.objects.get(id=clone_id)
        self.assertNotEqual(clone.id, plugin.id)
        # PluginMeta normalizes names to snake_case, e.g. 'sql_clone_default_(copy)'
        self.assertTrue(clone.name.startswith(name))
        self.assertIn("(copy)", clone.name)

    def test_base_clone_explicit_name(self):
        """Test cloning a plugin with an explicit name, and that the clone is a full copy."""
        plugin = self.new_api_plugin("api_clone_source")
        self.addCleanup(self.delete_plugin_by_name, "api_clone_target")
        clone_id = plugin.clone(new_name="api_clone_target")
        clone = ApiPlugin(plugin_id=clone_id, user_profile=self.user_profile)
        self.assertTrue(clone.ready)
        self.assertEqual(clone.name, "api_clone_target")
        self.assertEqual(clone.plugin_data.endpoint, plugin.plugin_data.endpoint)  # type: ignore[union-attr]
        self.assertEqual(clone.plugin_data.connection, plugin.plugin_data.connection)  # type: ignore[union-attr]
        self.assertEqual(clone.plugin_prompt.system_role, plugin.plugin_prompt.system_role)  # type: ignore[union-attr]
        self.assertEqual(clone.plugin_selector.directive, plugin.plugin_selector.directive)  # type: ignore[union-attr]
        self.assertNotEqual(clone.plugin_data.pk, plugin.plugin_data.pk)  # type: ignore[union-attr]

    def test_base_clone_copies_tags(self):
        """Test that cloning a plugin copies its tags."""
        plugin = self.new_sql_plugin("sql_clone_tags")
        self.addCleanup(self.delete_plugin_by_name, "sql_clone_tags_copy")
        clone = PluginMeta.objects.get(id=plugin.clone(new_name="sql_clone_tags_copy"))
        original_tags = {tag.name for tag in plugin.plugin_meta.tags.all()}  # type: ignore[union-attr]
        self.assertSetEqual({tag.name for tag in clone.tags.all()}, original_tags)

    def test_base_clone_leaves_original_intact(self):
        """Test that cloning a plugin does not modify the original."""
        plugin = self.new_sql_plugin("sql_clone_original")
        self.addCleanup(self.delete_plugin_by_name, "sql_clone_original_copy")
        plugin.clone(new_name="sql_clone_original_copy")
        self.assertEqual(PluginMeta.objects.get(id=plugin.id).name, "sql_clone_original")
        self.assertEqual(PluginDataSql.objects.get(plugin_id=plugin.id).sql_query, SQL_QUERY)

    def test_base_abstract_members(self):
        """Test that PluginBase's plugin data members must be implemented by a subclass."""
        plugin = ApiPlugin(plugin_id=self.api_plugin.id, user_profile=self.user_profile)
        for name in (
            "plugin_data_class",
            "plugin_data",
            "plugin_data_serializer",
            "plugin_data_serializer_class",
            "plugin_data_django_model",
        ):
            with self.subTest(member=name), self.assertRaises(NotImplementedError):
                getattr(PluginBase, name).fget(plugin)
