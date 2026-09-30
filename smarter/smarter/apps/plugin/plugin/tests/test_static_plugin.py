# pylint: disable=too-many-lines,protected-access
"""
Unit tests for :py:class:`smarter.apps.plugin.plugin.static.StaticPlugin`.

The structure of ``spec.data.staticData`` has semantic meaning. Its keys, including the
keys of nested dicts, are the *inquiry types* that the LLM can request via the
``inquiry_type`` parameter of the plugin's tool, and each key's value is the data returned
for that inquiry type. ``./data/static-plugin-edge-cases.yaml`` documents these semantics.
"""

from unittest import mock

from smarter.apps.plugin.manifest.enum import SAMPluginCommonMetadataClass
from smarter.apps.plugin.manifest.models.static_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.models import PluginDataStatic, PluginMeta
from smarter.apps.plugin.plugin.base import SmarterPluginError
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.apps.plugin.serializers import PluginStaticSerializer
from smarter.apps.plugin.signals import plugin_called, plugin_responded
from smarter.lib import json

from .base_classes import (
    STATIC_EDGE_CASES_PLUGIN_NAME,
    STATIC_PLUGIN_NAME,
    PluginTestBase,
    capture_signal,
)

GOBSTOPPER_INQUIRY_TYPES = ["contact", "biographical", "salesPromotions", "couponCodes"]
EDGE_CASE_INQUIRY_TYPES = [
    "name",
    "details",
    "color",
    "hours",
    "weekdays",
    "weekends",
    "holidays",
    "christmas",
    "newYears",
    "contact",
    "biographical",
    "founded",
    "rating",
    "isOpen",
    "discontinued",
    "emptyString",
    "emptyList",
    "emptyDict",
    "jsonObject",
    "jsonArray",
    "numericString",
    "booleanString",
    "nullString",
    "notJson",
    "unicode",
]


# pylint: disable=too-many-public-methods
class TestStaticPlugin(PluginTestBase):
    """Test StaticPlugin, using the shared StaticPlugin fixtures."""

    sql_fixtures = False
    api_fixtures = False
    static_fixtures = True

    def static_data(self, edge_cases: bool = False) -> dict:
        """Return the staticData of a test data manifest, normalized as it is stored in the database."""
        manifest = self.static_edge_cases_yaml if edge_cases else self.static_plugin_yaml
        return json.loads(json.dumps(manifest["spec"]["data"]["staticData"]))

    def ask(self, inquiry_type, edge_cases: bool = True):
        """Run a tool call for an inquiry type against a freshly loaded shared plugin."""
        return self.load_static_plugin(edge_cases=edge_cases).tool_call_fetch_plugin_response(
            {"inquiry_type": inquiry_type}
        )

    # =========================================================================
    # fixtures
    # =========================================================================
    def test_000_fixtures(self):
        """Test the class fixtures themselves, lest we get ahead of ourselves."""
        self.assertTrue(self.ready)
        for plugin in (self.static_plugin, self.static_edge_cases_plugin):
            self.assertIsInstance(plugin, StaticPlugin)
            self.assertTrue(plugin.ready)
        self.assertEqual(self.static_plugin.name, STATIC_PLUGIN_NAME)
        self.assertEqual(self.static_edge_cases_plugin.name, STATIC_EDGE_CASES_PLUGIN_NAME)

    def test_001_fixture_plugins_persisted(self):
        """Test that the shared plugins exist in the database."""
        for plugin in (self.static_plugin, self.static_edge_cases_plugin):
            self.assertTrue(PluginMeta.objects.filter(id=plugin.id).exists())
            self.assertTrue(PluginDataStatic.objects.filter(plugin_id=plugin.id).exists())

    # =========================================================================
    # class structure
    # =========================================================================
    def test_class_attributes(self):
        """Test the StaticPlugin class attributes."""
        self.assertIs(StaticPlugin.SAMPluginType, SAMStaticPlugin)
        self.assertEqual(self.static_plugin.kind, MANIFEST_KIND)
        self.assertIs(self.static_plugin.plugin_data_class, PluginDataStatic)
        self.assertIs(self.static_plugin.plugin_data_serializer_class, PluginStaticSerializer)

    def test_metadata_class(self):
        """Test that the plugin class is static."""
        self.assertEqual(self.load_static_plugin().metadata_class, SAMPluginCommonMetadataClass.STATIC.value)

    def test_has_no_orm_model_class(self):
        """Test that the misnamed ORMModelClass property, which returned a Pydantic class, has been removed."""
        self.assertFalse(hasattr(StaticPlugin, "ORMModelClass"))

    def test_plugin_data_serializer(self):
        """Test the StaticPlugin data serializer."""
        serializer = self.load_static_plugin().plugin_data_serializer
        self.assertIsInstance(serializer, PluginStaticSerializer)
        self.assertEqual(serializer.data["staticData"], self.static_data())  # type: ignore[union-attr]

    # =========================================================================
    # plugin data
    # =========================================================================
    def test_plugin_data(self):
        """Test the StaticPlugin data Django model."""
        plugin_data = self.load_static_plugin().plugin_data
        self.assertIsInstance(plugin_data, PluginDataStatic)
        self.assertEqual(plugin_data.static_data, self.static_data())  # type: ignore[union-attr]

    def test_plugin_data_description(self):
        """Test that the manifest description is persisted, since it becomes the tool description."""
        plugin_data = self.load_static_plugin().plugin_data
        self.assertEqual(plugin_data.description, self.static_plugin_yaml["metadata"]["description"])  # type: ignore[union-attr]

    def test_plugin_data_is_memoized(self):
        """Test that plugin_data returns the same instance on repeat access."""
        plugin = self.load_static_plugin()
        self.assertIs(plugin.plugin_data, plugin.plugin_data)

    def test_plugin_data_not_ready(self):
        """Test that plugin_data is None, rather than raising, for a plugin without a PluginMeta."""
        self.assertIsNone(StaticPlugin().plugin_data)

    def test_plugin_data_django_model(self):
        """Test the PluginDataStatic Django model dict constructed from the manifest."""
        model = self.static_plugin.plugin_data_django_model
        self.assertSetEqual(set(model.keys()), {"plugin", "description", "static_data"})  # type: ignore[union-attr]
        self.assertEqual(model["plugin"], self.static_plugin.plugin_meta)  # type: ignore[index]
        self.assertEqual(model["description"], self.static_plugin_yaml["metadata"]["description"])  # type: ignore[index]
        self.assertEqual(json.loads(json.dumps(model["static_data"])), self.static_data())  # type: ignore[index]

    def test_plugin_data_django_model_without_manifest(self):
        """Test that the Django model dict is None without a manifest."""
        self.assertIsNone(self.load_static_plugin().plugin_data_django_model)

    # =========================================================================
    # manifest and serialization
    # =========================================================================
    def test_manifest_from_database(self):
        """Test that the manifest is reconstructed from the database when not provided."""
        plugin = self.load_static_plugin()
        self.assertIsNone(plugin._manifest)
        manifest = plugin.manifest
        self.assertIsInstance(manifest, SAMStaticPlugin)
        self.assertEqual(manifest.metadata.name, STATIC_PLUGIN_NAME)  # type: ignore[union-attr]
        self.assertEqual(manifest.spec.data.staticData, self.static_data())  # type: ignore[union-attr]

    def test_manifest_not_ready(self):
        """Test that the manifest is None for a plugin that is not ready."""
        self.assertIsNone(StaticPlugin().manifest)

    def test_manifest_from_database_recreates_plugin(self):
        """Test that a manifest reconstructed from the database can create an equivalent plugin."""
        name = "static_recreated"
        self.addCleanup(self.delete_plugin_by_name, name)
        data = json.loads(self.load_static_plugin(edge_cases=True).manifest.model_dump_json())  # type: ignore[union-attr]
        data["metadata"]["name"] = name
        data.pop("status", None)
        plugin = StaticPlugin(manifest=SAMStaticPlugin(**data), user_profile=self.user_profile)
        self.assertCountEqual(plugin.inquiry_types, self.load_static_plugin(edge_cases=True).inquiry_types)
        self.assertEqual(plugin.plugin_data.static_data, self.static_data(edge_cases=True))  # type: ignore[union-attr]

    def test_to_json(self):
        """Test that to_json includes the static data section."""
        data = self.load_static_plugin().to_json()
        self.assertEqual(data["kind"], MANIFEST_KIND)  # type: ignore[index]
        self.assertEqual(data["spec"]["data"]["staticData"], self.static_data())  # type: ignore[index]

    def test_to_json_has_no_data_description(self):
        """Test that spec.data has no description, which would be redundant with metadata.description."""
        data = self.load_static_plugin().to_json()["spec"]["data"]  # type: ignore[index]
        self.assertEqual(list(data.keys()), ["staticData"])

    def test_plugin_data_serializer_fields(self):
        """Test that the serializer, which renders spec.data, exposes only the static data."""
        self.assertEqual(list(self.load_static_plugin().plugin_data_serializer.data.keys()), ["staticData"])  # type: ignore[union-attr]

    def test_test_data_has_no_data_description(self):
        """Test that the test data manifests follow the convention of no spec.data.description."""
        for manifest in (self.static_plugin_yaml, self.static_edge_cases_yaml):
            self.assertNotIn("description", manifest["spec"]["data"])

    def test_to_json_validates_as_manifest(self):
        """Test that to_json produces a valid SAMStaticPlugin manifest."""
        self.assertIsInstance(SAMStaticPlugin(**self.load_static_plugin().to_json()), SAMStaticPlugin)  # type: ignore[arg-type]

    # =========================================================================
    # inquiry types
    # =========================================================================
    def test_inquiry_types(self):
        """Test that the inquiry types are the top-level keys of the static data."""
        self.assertCountEqual(self.load_static_plugin().inquiry_types, GOBSTOPPER_INQUIRY_TYPES)

    def test_inquiry_types_include_nested_dict_keys(self):
        """Test that the keys of nested dicts, at any depth, are inquiry types."""
        inquiry_types = self.load_static_plugin(edge_cases=True).inquiry_types
        for key in ("details", "color", "hours", "weekdays", "holidays", "christmas", "newYears"):
            self.assertIn(key, inquiry_types)

    def test_inquiry_types_exclude_keys_inside_lists(self):
        """Test that the keys of dicts inside lists are not inquiry types."""
        inquiry_types = self.load_static_plugin(edge_cases=True).inquiry_types
        self.assertNotIn("phone", inquiry_types)
        self.assertNotIn("email", inquiry_types)

    def test_inquiry_types_are_unique(self):
        """Test that a key used at more than one level appears only once."""
        inquiry_types = self.load_static_plugin(edge_cases=True).inquiry_types
        self.assertEqual(len(inquiry_types), len(set(inquiry_types)))
        self.assertEqual(inquiry_types.count("name"), 1)

    def test_inquiry_types_edge_cases(self):
        """Test the complete set of inquiry types of the edge cases plugin."""
        self.assertCountEqual(self.load_static_plugin(edge_cases=True).inquiry_types, EDGE_CASE_INQUIRY_TYPES)

    def test_inquiry_types_are_strings(self):
        """Test that inquiry types are strings, as required by the tool's JSON schema."""
        for inquiry_type in self.load_static_plugin(edge_cases=True).inquiry_types:
            self.assertIsInstance(inquiry_type, str)

    def test_inquiry_types_not_ready(self):
        """Test that a plugin without data has no inquiry types."""
        self.assertEqual(StaticPlugin().inquiry_types, [])

    def test_inquiry_types_empty_static_data(self):
        """Test that a plugin with empty static data has no inquiry types."""
        self.assertEqual(self.new_static_plugin("static_empty", static_data={}).inquiry_types, [])

    def test_inquiry_types_reflect_updated_static_data(self):
        """Test that inquiry types are not served from a stale cache after the static data changes."""
        name = "static_updated"
        plugin = self.new_static_plugin(name, static_data={"before": 1})
        self.assertEqual(plugin.inquiry_types, ["before"])
        StaticPlugin(manifest=self.static_manifest(name, static_data={"after": 2}), user_profile=self.user_profile)
        reloaded = StaticPlugin(plugin_id=plugin.id, user_profile=self.user_profile)
        self.assertEqual(reloaded.inquiry_types, ["after"])
        self.assertEqual(reloaded.tool_call_fetch_plugin_response({"inquiry_type": "after"}), "2")
        with self.assertRaises(SmarterPluginError):
            reloaded.tool_call_fetch_plugin_response({"inquiry_type": "before"})

    # =========================================================================
    # custom tool
    # =========================================================================
    def test_custom_tool(self):
        """Test the OpenAI function calling tool definition."""
        plugin = self.load_static_plugin()
        tool = plugin.custom_tool
        self.assertEqual(tool["type"], "function")  # type: ignore[index]
        function = tool["function"]  # type: ignore[index]
        self.assertEqual(function["name"], plugin.function_calling_identifier)
        self.assertEqual(function["parameters"]["type"], "object")
        self.assertEqual(function["parameters"]["required"], ["inquiry_type"])
        self.assertEqual(function["parameters"]["properties"]["inquiry_type"]["type"], "string")

    def test_custom_tool_enum(self):
        """Test that the inquiry_type enum is the plugin's inquiry types."""
        plugin = self.load_static_plugin()
        enum = plugin.custom_tool["function"]["parameters"]["properties"]["inquiry_type"]["enum"]  # type: ignore[index]
        self.assertEqual(enum, plugin.inquiry_types)
        self.assertCountEqual(enum, GOBSTOPPER_INQUIRY_TYPES)

    def test_custom_tool_description(self):
        """Test that the tool description is the manifest description."""
        description = self.load_static_plugin().custom_tool["function"]["description"]  # type: ignore[index]
        self.assertEqual(description, self.static_plugin_yaml["metadata"]["description"])

    def test_custom_tool_description_fallback(self):
        """Test that the tool description falls back to the PluginMeta description when the data has none."""
        plugin = self.load_static_plugin()
        plugin.plugin_data.description = ""  # type: ignore[union-attr]
        description = plugin.custom_tool["function"]["description"]  # type: ignore[index]
        self.assertEqual(description, plugin.plugin_meta.description)  # type: ignore[union-attr]
        self.assertTrue(description)

    def test_custom_tool_without_inquiry_types_omits_enum(self):
        """Test that the enum is omitted, rather than null, when there are no inquiry types."""
        tool = self.new_static_plugin("static_no_inquiry_types", static_data={}).custom_tool
        inquiry_type = tool["function"]["parameters"]["properties"]["inquiry_type"]  # type: ignore[index]
        self.assertNotIn("enum", inquiry_type)

    def test_custom_tool_is_json_serializable(self):
        """Test that the tool can be sent to the OpenAI api as JSON."""
        tool = self.load_static_plugin(edge_cases=True).custom_tool
        self.assertEqual(json.loads(json.dumps(tool)), tool)

    def test_custom_tool_not_ready(self):
        """Test that the tool is None for a plugin that is not ready."""
        self.assertIsNone(StaticPlugin().custom_tool)

    def test_every_advertised_inquiry_type_resolves(self):
        """
        Test the contract between custom_tool and tool_call_fetch_plugin_response: every.

        inquiry type offered to the LLM in the tool's enum can be requested without error.
        """
        for edge_cases in (False, True):
            plugin = self.load_static_plugin(edge_cases=edge_cases)
            enum = plugin.custom_tool["function"]["parameters"]["properties"]["inquiry_type"]["enum"]  # type: ignore[index]
            for inquiry_type in enum:
                retval = plugin.tool_call_fetch_plugin_response({"inquiry_type": inquiry_type})
                self.assertIsInstance(retval, (dict, list, str), f"inquiry_type={inquiry_type}")

    # =========================================================================
    # tool calls, the Everlasting Gobstopper
    # =========================================================================
    def test_tool_call_each_inquiry_type(self):
        """Test that each inquiry type returns its static data."""
        static_data = self.static_data()
        for inquiry_type in GOBSTOPPER_INQUIRY_TYPES:
            self.assertEqual(self.ask(inquiry_type, edge_cases=False), static_data[inquiry_type], inquiry_type)

    def test_tool_call_list_value(self):
        """Test that a list value is returned as a list."""
        coupon_codes = self.ask("couponCodes", edge_cases=False)
        self.assertIsInstance(coupon_codes, list)
        self.assertEqual({coupon["code"] for coupon in coupon_codes}, {"10OFF", "20OFF"})  # type: ignore[union-attr]

    def test_tool_call_string_value(self):
        """Test that a folded yaml string is returned as-is."""
        biographical = self.ask("biographical", edge_cases=False)
        self.assertIsInstance(biographical, str)
        self.assertTrue(biographical.startswith("Willy Wonka is a fictional character"))  # type: ignore[union-attr]

    def test_tool_call_json_string_args(self):
        """Test a tool call with a JSON string of arguments, as sent by OpenAI."""
        retval = self.load_static_plugin().tool_call_fetch_plugin_response('{"inquiry_type": "couponCodes"}')
        self.assertEqual(retval, self.static_data()["couponCodes"])

    def test_tool_call_extra_args_are_ignored(self):
        """Test that arguments other than inquiry_type are ignored."""
        retval = self.load_static_plugin().tool_call_fetch_plugin_response(
            {"inquiry_type": "couponCodes", "unexpected": "value"}
        )
        self.assertEqual(retval, self.static_data()["couponCodes"])

    # =========================================================================
    # tool calls, the static data edge cases
    # =========================================================================
    def test_tool_call_nested_inquiry_type(self):
        """Test that a nested dict key can be requested directly."""
        self.assertEqual(self.ask("weekdays"), "9am - 5pm")
        self.assertEqual(self.ask("christmas"), "closed")

    def test_tool_call_dict_value(self):
        """Test that a dict value is returned as a dict, including its nested dicts."""
        self.assertEqual(self.ask("hours"), self.static_data(edge_cases=True)["hours"])
        self.assertEqual(self.ask("holidays"), {"christmas": "closed", "newYears": "10am - 2pm"})

    def test_tool_call_shallower_key_takes_precedence(self):
        """Test that a top-level key takes precedence over a nested key of the same name."""
        self.assertEqual(self.ask("name"), "Top Level Name")

    def test_tool_call_key_inside_list_is_not_found(self):
        """Test that the key of a dict inside a list cannot be requested."""
        with self.assertRaises(SmarterPluginError):
            self.ask("phone")

    def test_tool_call_integer_value(self):
        """Test that an integer value is returned as a string."""
        self.assertEqual(self.ask("founded"), "1964")

    def test_tool_call_float_value(self):
        """Test that a float value is returned as a string."""
        self.assertEqual(self.ask("rating"), "4.5")

    def test_tool_call_boolean_value(self):
        """Test that a boolean value is returned as a JSON string."""
        self.assertEqual(self.ask("isOpen"), "true")

    def test_tool_call_null_value(self):
        """Test that a null value is returned as an empty string, rather than raising."""
        self.assertEqual(self.ask("discontinued"), "")

    def test_tool_call_empty_values(self):
        """Test that empty values are returned as-is."""
        self.assertEqual(self.ask("emptyString"), "")
        self.assertEqual(self.ask("emptyList"), [])
        self.assertEqual(self.ask("emptyDict"), {})

    def test_tool_call_json_object_string_is_decoded(self):
        """Test that a string containing a JSON object is decoded."""
        self.assertEqual(self.ask("jsonObject"), {"a": 1, "b": [2, 3]})

    def test_tool_call_json_array_string_is_decoded(self):
        """Test that a string containing a JSON array is decoded."""
        self.assertEqual(self.ask("jsonArray"), [1, 2, 3])

    def test_tool_call_json_literal_strings_are_not_decoded(self):
        """Test that strings containing JSON literals are returned as-is, rather than raising."""
        self.assertEqual(self.ask("numericString"), "42")
        self.assertEqual(self.ask("booleanString"), "true")
        self.assertEqual(self.ask("nullString"), "null")

    def test_tool_call_malformed_json_string(self):
        """Test that a string that merely looks like JSON is returned as-is."""
        self.assertEqual(self.ask("notJson"), "{not json")

    def test_tool_call_unicode_value(self):
        """Test that unicode values round trip."""
        self.assertEqual(self.ask("unicode"), "Café ☕ – ünïcödé")

    def test_tool_call_folded_string_keeps_trailing_newline(self):
        """Test that string values are not altered."""
        self.assertEqual(self.ask("biographical"), "A folded yaml string, which ends with a newline.\n")

    # =========================================================================
    # tool calls, invalid arguments and states
    # =========================================================================
    def test_tool_call_unknown_inquiry_type(self):
        """Test that an unknown inquiry type raises, listing the available inquiry types."""
        with self.assertRaises(SmarterPluginError) as context:
            self.ask("noSuchInquiryType", edge_cases=False)
        for inquiry_type in GOBSTOPPER_INQUIRY_TYPES:
            self.assertIn(inquiry_type, str(context.exception))

    def test_tool_call_unknown_inquiry_type_does_not_dump_static_data(self):
        """Test that the error message does not include the entire static data."""
        with self.assertRaises(SmarterPluginError) as context:
            self.ask("noSuchInquiryType", edge_cases=False)
        self.assertNotIn("Willy Wonka is a fictional character", str(context.exception))

    def test_tool_call_inquiry_type_is_case_sensitive(self):
        """Test that inquiry types are matched exactly."""
        with self.assertRaises(SmarterPluginError):
            self.ask("CouponCodes", edge_cases=False)

    def test_tool_call_missing_inquiry_type(self):
        """Test that missing arguments raise."""
        for function_args in ({}, None, "", '{"other": 1}'):
            with self.assertRaises(SmarterPluginError, msg=f"function_args={function_args!r}"):
                self.load_static_plugin().tool_call_fetch_plugin_response(function_args)

    def test_tool_call_inquiry_type_not_a_string(self):
        """Test that a non-string inquiry type raises."""
        for inquiry_type in (1, None, ["contact"], {"contact": 1}):
            with self.assertRaises(SmarterPluginError, msg=f"inquiry_type={inquiry_type!r}"):
                self.ask(inquiry_type, edge_cases=False)

    def test_tool_call_invalid_json_string_args(self):
        """Test that a malformed JSON string of arguments raises."""
        with self.assertRaises(SmarterPluginError):
            self.load_static_plugin().tool_call_fetch_plugin_response("{not json")

    def test_tool_call_invalid_args_type(self):
        """Test that arguments of an unsupported type raise."""
        for function_args in (42, ["contact"], '["contact"]'):
            with self.assertRaises(SmarterPluginError, msg=f"function_args={function_args!r}"):
                self.load_static_plugin().tool_call_fetch_plugin_response(function_args)  # type: ignore[arg-type]

    def test_tool_call_not_ready(self):
        """Test that a tool call on a plugin that is not ready raises."""
        with self.assertRaises(SmarterPluginError):
            StaticPlugin().tool_call_fetch_plugin_response({"inquiry_type": "contact"})

    def test_tool_call_no_plugin_data(self):
        """Test that a tool call without plugin data raises."""
        plugin = self.load_static_plugin()
        with mock.patch.object(StaticPlugin, "plugin_data", new_callable=mock.PropertyMock, return_value=None):
            with self.assertRaises(SmarterPluginError):
                plugin.tool_call_fetch_plugin_response({"inquiry_type": "contact"})

    def test_tool_call_invalid_static_data(self):
        """Test that static data that is neither a dict nor a list raises a SmarterPluginError."""
        plugin = self.load_static_plugin()
        plugin.plugin_data.static_data = "not a dict"  # type: ignore[union-attr]
        with self.assertRaises(SmarterPluginError):
            plugin.tool_call_fetch_plugin_response({"inquiry_type": "contact"})

    def test_tool_call_list_static_data(self):
        """
        Test static data stored as a list of dicts, which cannot be created from a manifest.

        Each record is keyed by the value of its first field, and, as documented by
        list_of_dicts_to_dict(), maps to that same value rather than to the record.
        """
        plugin = self.load_static_plugin()
        plugin.plugin_data.static_data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 40}]  # type: ignore[union-attr]
        self.assertEqual(plugin.inquiry_types, ["Alice", "Bob"])
        self.assertEqual(plugin.tool_call_fetch_plugin_response({"inquiry_type": "Alice"}), "Alice")

    # =========================================================================
    # tool calls, signals
    # =========================================================================
    def test_tool_call_sends_signals(self):
        """Test that a tool call sends plugin_called and plugin_responded."""
        with capture_signal(plugin_called) as called, capture_signal(plugin_responded) as responded:
            retval = self.ask("couponCodes", edge_cases=False)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0]["inquiry_type"], "couponCodes")
        self.assertEqual(len(responded), 1)
        self.assertEqual(responded[0]["inquiry_type"], "couponCodes")
        self.assertEqual(responded[0]["response"], retval)

    def test_tool_call_unknown_inquiry_type_sends_no_response_signal(self):
        """Test that a failed tool call sends plugin_called, but not plugin_responded."""
        with capture_signal(plugin_called) as called, capture_signal(plugin_responded) as responded:
            with self.assertRaises(SmarterPluginError):
                self.ask("noSuchInquiryType", edge_cases=False)
        self.assertEqual(len(called), 1)
        self.assertEqual(responded, [])

    def test_tool_call_invalid_args_sends_no_signals(self):
        """Test that a tool call with invalid arguments sends no signals."""
        with capture_signal(plugin_called) as called, capture_signal(plugin_responded) as responded:
            with self.assertRaises(SmarterPluginError):
                self.load_static_plugin().tool_call_fetch_plugin_response({})
        self.assertEqual(called, [])
        self.assertEqual(responded, [])

    # =========================================================================
    # find_inquiry_value()
    # =========================================================================
    def test_find_inquiry_value_top_level(self):
        """Test finding a top-level key."""
        self.assertEqual(StaticPlugin.find_inquiry_value({"a": 1}, "a"), (True, 1))

    def test_find_inquiry_value_nested(self):
        """Test finding keys of nested dicts at any depth."""
        data = {"a": {"b": {"c": 3}}}
        self.assertEqual(StaticPlugin.find_inquiry_value(data, "b"), (True, {"c": 3}))
        self.assertEqual(StaticPlugin.find_inquiry_value(data, "c"), (True, 3))

    def test_find_inquiry_value_precedence(self):
        """Test that keys at the current level take precedence over nested keys."""
        data = {"nested": {"key": "nested"}, "key": "top"}
        self.assertEqual(StaticPlugin.find_inquiry_value(data, "key"), (True, "top"))

    def test_find_inquiry_value_sibling_order(self):
        """Test that the first nested dict containing a key wins."""
        data = {"first": {"key": 1}, "second": {"key": 2}}
        self.assertEqual(StaticPlugin.find_inquiry_value(data, "key"), (True, 1))

    def test_find_inquiry_value_none(self):
        """Test that a key whose value is None is found."""
        self.assertEqual(StaticPlugin.find_inquiry_value({"a": None}, "a"), (True, None))

    def test_find_inquiry_value_missing(self):
        """Test that a missing key is not found."""
        self.assertEqual(StaticPlugin.find_inquiry_value({"a": {"b": 1}}, "z"), (False, None))

    def test_find_inquiry_value_does_not_search_lists(self):
        """Test that dicts inside lists are not searched, consistent with inquiry_types."""
        self.assertEqual(StaticPlugin.find_inquiry_value({"a": [{"b": 1}]}, "b"), (False, None))

    def test_find_inquiry_value_empty(self):
        """Test searching empty static data."""
        self.assertEqual(StaticPlugin.find_inquiry_value({}, "a"), (False, None))

    # =========================================================================
    # to_tool_response()
    # =========================================================================
    def test_to_tool_response(self):
        """Test converting static data values to tool call responses."""
        expectations = [
            ({"a": 1}, {"a": 1}),
            ([1, 2], [1, 2]),
            ("text", "text"),
            ("", ""),
            (None, ""),
            (0, "0"),
            (42, "42"),
            (-1.5, "-1.5"),
            (True, "true"),
            (False, "false"),
            ('{"a": 1}', {"a": 1}),
            ("  [1, 2]  ", [1, 2]),
            ("42", "42"),
            ("true", "true"),
            ("null", "null"),
            ('"quoted"', '"quoted"'),
            ("{not json", "{not json"),
            ("[not json", "[not json"),
        ]
        for value, expected in expectations:
            self.assertEqual(StaticPlugin.to_tool_response(value), expected, f"value={value!r}")

    def test_to_tool_response_types(self):
        """Test that tool call responses are always a dict, list or str."""
        for value in ({}, [], "", None, 0, 1.5, True, "{}", "[]", "x"):
            self.assertIsInstance(StaticPlugin.to_tool_response(value), (dict, list, str), f"value={value!r}")

    # =========================================================================
    # example manifest
    # =========================================================================
    def test_example_manifest(self):
        """Test that the example manifest is a valid SAMStaticPlugin."""
        example = StaticPlugin.example_manifest()
        self.assertIsInstance(example, dict)
        self.assertEqual(example["kind"], MANIFEST_KIND)  # type: ignore[index]
        self.assertIsInstance(SAMStaticPlugin(**example), SAMStaticPlugin)  # type: ignore[arg-type]

    def test_example_manifest_creates_a_working_plugin(self):
        """Test that the example manifest creates a plugin whose inquiry types all resolve."""
        name = "static_from_example"
        self.addCleanup(self.delete_plugin_by_name, name)
        example = StaticPlugin.example_manifest()
        example["metadata"]["name"] = name  # type: ignore[index]
        example.pop("status", None)  # type: ignore[union-attr]
        plugin = StaticPlugin(manifest=SAMStaticPlugin(**example), user_profile=self.user_profile)  # type: ignore[arg-type]
        self.assertCountEqual(plugin.inquiry_types, ["contact", "biographical", "sales_promotions", "coupon_codes"])
        for inquiry_type in plugin.inquiry_types:
            plugin.tool_call_fetch_plugin_response({"inquiry_type": inquiry_type})

    # =========================================================================
    # lifecycle
    # =========================================================================
    def test_create_persists_static_data(self):
        """Test that creating a plugin persists its static data and description."""
        plugin = self.new_static_plugin("static_create", static_data={"a": {"b": 1}})
        plugin_data = PluginDataStatic.objects.get(plugin_id=plugin.id)
        self.assertEqual(plugin_data.static_data, {"a": {"b": 1}})
        self.assertEqual(plugin_data.description, self.static_plugin_yaml["metadata"]["description"])

    def test_update_replaces_static_data(self):
        """Test that re-applying a manifest replaces the static data."""
        name = "static_update"
        plugin = self.new_static_plugin(name, static_data={"a": 1})
        StaticPlugin(manifest=self.static_manifest(name, static_data={"b": 2}), user_profile=self.user_profile)
        self.assertEqual(PluginDataStatic.objects.get(plugin_id=plugin.id).static_data, {"b": 2})
        self.assertEqual(PluginMeta.objects.filter(user_profile__account=self.account, name=name).count(), 1)

    def test_clone_copies_static_data(self):
        """Test that cloning a plugin copies its static data and leaves the original intact."""
        plugin = self.new_static_plugin("static_clone_source", static_data={"a": 1})
        clone_id = plugin.clone(new_name="static_clone_target")
        self.addCleanup(self.delete_plugin_by_id, clone_id)
        self.assertEqual(PluginDataStatic.objects.get(plugin_id=clone_id).static_data, {"a": 1})
        self.assertEqual(PluginDataStatic.objects.get(plugin_id=plugin.id).static_data, {"a": 1})
        clone = StaticPlugin(plugin_id=clone_id, user_profile=self.user_profile)
        self.assertEqual(clone.tool_call_fetch_plugin_response({"inquiry_type": "a"}), "1")

    def test_delete(self):
        """Test that deleting a plugin removes its static data."""
        plugin = self.new_static_plugin("static_delete")
        plugin_id = plugin.id
        self.assertTrue(plugin.delete())
        self.assertFalse(PluginMeta.objects.filter(id=plugin_id).exists())
        self.assertFalse(PluginDataStatic.objects.filter(plugin_id=plugin_id).exists())
