# pylint: disable=wrong-import-position
# pylint: disable=R0801,W0613
"""Test providers."""

# python stuff
import json
import unittest
from time import sleep

from pydantic_core import ValidationError as PydanticValidationError

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
)
from smarter.apps.chat.providers.const import OpenAIMessageKeys
from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonSpecPromptKeys,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
    SAMPluginCommonSpecSelectorKeys,
    SAMPluginSpecKeys,
)
from smarter.apps.plugin.models import (
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.apps.plugin.plugin.base import SmarterPluginError
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.apps.plugin.plugin.utils import PluginExamples
from smarter.apps.plugin.serializers import (
    PluginMetaSerializer,
    PluginPromptSerializer,
    PluginSelectorSerializer,
    PluginStaticSerializer,
)
from smarter.apps.plugin.signals import (
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_ready,
    plugin_selected,
    plugin_updated,
)
from smarter.apps.plugin.tests.test_setup import get_test_file_path
from smarter.apps.plugin.utils import add_example_plugins
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.loader import SAMLoaderError
from smarter.lib.unittest.utils import get_readonly_yaml_file


# pylint: disable=too-many-public-methods,too-many-instance-attributes
class TestPlugin(unittest.TestCase):
    """Test plugin."""

    data: dict
    user_profile: UserProfile

    _plugin_called = False
    _plugin_cloned = False
    _plugin_created = False
    _plugin_deleted = False
    _plugin_ready = False
    _plugin_selected = False
    _plugin_selected_called = False
    _plugin_updated = False

    def plugin_called_signal_handler(self, *args, **kwargs):
        self._plugin_called = True

    def plugin_cloned_signal_handler(self, *args, **kwargs):
        self._plugin_cloned = True

    def plugin_created_signal_handler(self, *args, **kwargs):
        self._plugin_created = True

    def plugin_deleted_signal_handler(self, *args, **kwargs):
        self._plugin_deleted = True

    def plugin_ready_signal_handler(self, *args, **kwargs):
        self._plugin_ready = True

    def plugin_selected_signal_handler(self, *args, **kwargs):
        self._plugin_selected = True

    def plugin_selected_called_signal_handler(self, *args, **kwargs):
        self._plugin_selected_called = True

    def plugin_updated_signal_handler(self, *args, **kwargs):
        self._plugin_updated = True

    @property
    def signals(self):
        return {
            "plugin_called": self._plugin_called,
            "plugin_cloned": self._plugin_cloned,
            "plugin_created": self._plugin_created,
            "plugin_deleted": self._plugin_deleted,
            "plugin_ready": self._plugin_ready,
            "plugin_selected": self._plugin_selected,
            "plugin_updated": self._plugin_updated,
        }

    def setUp(self):
        """Set up test fixtures."""
        config_path = get_test_file_path("everlasting-gobstopper.yaml")
        self.data = get_readonly_yaml_file(config_path)
        self.user, self.account, self.user_profile = admin_user_factory()

    def tearDown(self):
        """Clean up test fixtures."""
        factory_account_teardown(self.user, self.account, self.user_profile)

    # pylint: disable=broad-exception-caught
    def test_create(self):
        """Test that we can create a plugin using the StaticPlugin."""

        plugin_created.connect(self.plugin_created_signal_handler, dispatch_uid="plugin_created_test_create")
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_create")

        plugin = StaticPlugin(data=self.data)

        # sleep long enough to eliminate race situation
        # between the asynchronous commit and our assertion
        sleep(1)

        # verify that the signals were sent
        self.assertTrue(self.signals["plugin_created"])
        self.assertTrue(self.signals["plugin_ready"])

        self.assertIsInstance(plugin, StaticPlugin)
        self.assertTrue(plugin.ready)
        self.assertIsInstance(plugin.plugin_meta, PluginMeta)
        self.assertIsInstance(plugin.plugin_selector, PluginSelector)
        self.assertIsInstance(plugin.plugin_prompt, PluginPrompt)
        self.assertIsInstance(plugin.plugin_data, PluginDataStatic)
        self.assertIsInstance(plugin.plugin_data_serializer, PluginStaticSerializer)
        self.assertIsInstance(plugin.plugin_meta_serializer, PluginMetaSerializer)
        self.assertIsInstance(plugin.plugin_prompt_serializer, PluginPromptSerializer)
        self.assertIsInstance(plugin.plugin_selector_serializer, PluginSelectorSerializer)

        self.assertEqual(plugin.plugin_meta.name, self.data[SAMKeys.METADATA.value]["name"])
        self.assertEqual(
            plugin.plugin_selector.directive,
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.SELECTOR.value][
                SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value
            ],
        )
        self.assertEqual(
            plugin.plugin_prompt.provider,
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][SAMPluginCommonSpecPromptKeys.PROVIDER.value],
        )
        self.assertEqual(
            plugin.plugin_prompt.system_role,
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value
            ],
        )
        self.assertEqual(
            plugin.plugin_prompt.model,
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][SAMPluginCommonSpecPromptKeys.MODEL.value],
        )
        self.assertEqual(
            plugin.plugin_prompt.temperature,
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.TEMPERATURE.value
            ],
        )
        self.assertEqual(
            plugin.plugin_prompt.max_tokens,
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.MAXTOKENS.value
            ],
        )
        self.assertEqual(
            plugin.plugin_data.description, self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.DATA.value]["description"]
        )
        self.assertEqual(
            plugin.plugin_data.static_data, self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.DATA.value]["staticData"]
        )

    def test_to_json(self):
        """Test that the StaticPlugin generates correct JSON output."""
        plugin_created.connect(self.plugin_created_signal_handler, dispatch_uid="plugin_created_test_to_json")
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_to_json")

        plugin = StaticPlugin(user_profile=self.user_profile, data=self.data)
        to_json = plugin.to_json()

        # verify that signal was sent
        self.assertTrue(self.signals["plugin_created"])
        self.assertTrue(self.signals["plugin_ready"])

        self.assertIsInstance(to_json, dict)
        self.assertEqual(to_json[SAMKeys.METADATA.value]["name"], self.data[SAMKeys.METADATA.value]["name"])
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.SELECTOR.value][
                SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value
            ].strip(),
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.SELECTOR.value][
                SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value
            ].strip(),
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.PROVIDER.value
            ].strip(),
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.PROVIDER.value
            ].strip(),
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value
            ].strip(),
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value
            ].strip(),
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.MODEL.value
            ].strip(),
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.MODEL.value
            ].strip(),
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.TEMPERATURE.value
            ],
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.TEMPERATURE.value
            ],
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][SAMPluginCommonSpecPromptKeys.MAXTOKENS.value],
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.MAXTOKENS.value
            ],
        )

    def test_delete(self):
        """Test that we can delete a plugin using the StaticPlugin."""
        plugin_created.connect(self.plugin_created_signal_handler, dispatch_uid="plugin_created_test_delete")
        plugin_updated.connect(self.plugin_updated_signal_handler, dispatch_uid="plugin_updated_test_delete")
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_delete")
        plugin_deleted.connect(self.plugin_deleted_signal_handler, dispatch_uid="plugin_deleted_test_delete")

        plugin = StaticPlugin(data=self.data)
        plugin_id = plugin.id
        plugin.delete()

        # sleep long enough to eliminate race situation
        # between the asynchronous commit and our assertion
        sleep(1)

        # verify that the signals were sent
        self.assertTrue(self.signals["plugin_created"] or self.signals["plugin_updated"])
        self.assertTrue(self.signals["plugin_ready"])
        self.assertTrue(self.signals["plugin_deleted"])

        with self.assertRaises(PluginMeta.DoesNotExist):
            PluginMeta.objects.get(pk=plugin_id)

        with self.assertRaises(PluginSelector.DoesNotExist):
            PluginSelector.objects.get(plugin_id=plugin_id)

        with self.assertRaises(PluginPrompt.DoesNotExist):
            PluginPrompt.objects.get(plugin_id=plugin_id)

        with self.assertRaises(PluginDataStatic.DoesNotExist):
            PluginDataStatic.objects.get(plugin_id=plugin_id)

    def test_add_sample_plugins(self):
        """Test utility function to add sample plugins to a user account."""

        # add the sample plugins to the user account
        add_example_plugins(user_profile=self.user_profile)

        # verify that all of the sample plugins were added to the user account
        plugins = PluginMeta.objects.filter(account=self.account)
        self.assertEqual(len(plugins), PluginExamples().count())

        # verify that all of the sample plugins were correctdly created
        # and are in a ready state.
        for plugin in plugins:
            self.assertTrue(StaticPlugin(plugin_meta=plugin).ready)

    # pylint: disable=too-many-statements
    def test_validation_bad_structure(self):
        """Test that the StaticPlugin raises an error when given bad data."""
        with self.assertRaises(SmarterPluginError):
            StaticPlugin(data={})

        bad_data = self.data.copy()
        bad_data.pop(SAMKeys.METADATA.value)
        with self.assertRaises(SAMLoaderError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value].pop(SAMPluginSpecKeys.SELECTOR.value)
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value].pop(SAMPluginSpecKeys.PROMPT.value)
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value].pop(SAMPluginSpecKeys.DATA.value)
        with self.assertRaises(SAMLoaderError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.METADATA.value].pop("name")
        with self.assertRaises(SAMLoaderError):
            StaticPlugin(data=bad_data)

    def test_pydantic_validation_errors(self):
        """Test that the StaticPlugin raises an error when given bad data."""

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.SELECTOR.value].pop(
            SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value
        )
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value].pop(SAMPluginCommonSpecPromptKeys.PROVIDER.value)
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value].pop(SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value)
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value].pop(SAMPluginCommonSpecPromptKeys.MODEL.value)
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value].pop(
            SAMPluginCommonSpecPromptKeys.TEMPERATURE.value
        )
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value].pop(SAMPluginCommonSpecPromptKeys.MAXTOKENS.value)
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.DATA.value].pop("description")
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.DATA.value].pop("staticData")
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

    def test_validation_bad_data_types(self):
        """Test that the StaticPlugin raises an error when given bad data."""
        bad_data = self.data.copy()
        bad_data[SAMKeys.METADATA.value]["tags"] = "not a list"
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.SELECTOR.value][
            SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value
        ] = "not a list"
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
            SAMPluginCommonSpecPromptKeys.TEMPERATURE.value
        ] = "not a float"
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

        bad_data = self.data.copy()
        bad_data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
            SAMPluginCommonSpecPromptKeys.MAXTOKENS.value
        ] = "not an int"
        with self.assertRaises(PydanticValidationError):
            StaticPlugin(data=bad_data)

    def test_clone(self):
        """Test that we can clone a plugin using the StaticPlugin."""
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_clone")
        plugin_cloned.connect(self.plugin_cloned_signal_handler, dispatch_uid="plugin_cloned_test_clone")

        plugin = StaticPlugin(data=self.data)
        clone_id = plugin.clone()
        plugin_clone = StaticPlugin(plugin_id=clone_id)

        # sleep long enough to eliminate race situation
        # between the asynchronous commit and our assertion
        sleep(1)

        # verify that the signals were sent
        self.assertTrue(self.signals["plugin_ready"])
        self.assertTrue(self.signals["plugin_cloned"])

        self.assertNotEqual(plugin.id, plugin_clone.id)
        self.assertNotEqual(plugin.plugin_meta.name, plugin_clone.plugin_meta.name)
        self.assertNotEqual(plugin.plugin_meta.created_at, plugin_clone.plugin_meta.created_at)

        self.assertEqual(plugin.plugin_meta.author, plugin_clone.plugin_meta.author)
        self.assertListEqual(list(plugin.plugin_meta.tags.all()), list(plugin_clone.plugin_meta.tags.all()))

        self.assertEqual(plugin.plugin_selector.directive, plugin_clone.plugin_selector.directive)
        self.assertEqual(plugin.plugin_selector.search_terms, plugin_clone.plugin_selector.search_terms)

        self.assertEqual(plugin.plugin_prompt.system_role, plugin_clone.plugin_prompt.system_role)
        self.assertEqual(plugin.plugin_prompt.model, plugin_clone.plugin_prompt.model)
        self.assertEqual(plugin.plugin_prompt.temperature, plugin_clone.plugin_prompt.temperature)
        self.assertEqual(plugin.plugin_prompt.max_tokens, plugin_clone.plugin_prompt.max_tokens)

        self.assertEqual(plugin.plugin_data.description, plugin_clone.plugin_data.description)
        self.assertEqual(plugin.plugin_data.static_data, plugin_clone.plugin_data.static_data)

        plugin.delete()
        plugin_clone.delete()

    def test_json_serialization(self):
        """Test that the StaticPlugin generates correct JSON output."""
        plugin_ready.connect(self.plugin_ready_signal_handler, dispatch_uid="plugin_ready_test_json_serialization")

        plugin = StaticPlugin(data=self.data)
        to_json = plugin.to_json()

        # verify that signal was sent
        self.assertTrue(self.signals["plugin_ready"])

        # ensure that we can go from json output to a string and back to json without error
        to_json = json.loads(json.dumps(to_json))

        # ensure that the json output still matches the original data
        self.assertIsInstance(to_json, dict)
        self.assertEqual(to_json[SAMKeys.METADATA.value]["name"], self.data[SAMKeys.METADATA.value]["name"])
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.SELECTOR.value][
                SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value
            ].strip(),
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.SELECTOR.value][
                SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value
            ].strip(),
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.PROVIDER.value
            ].strip(),
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.PROVIDER.value
            ].strip(),
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value
            ].strip(),
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value
            ].strip(),
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.MODEL.value
            ].strip(),
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.MODEL.value
            ].strip(),
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.TEMPERATURE.value
            ],
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.TEMPERATURE.value
            ],
        )
        self.assertEqual(
            to_json[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][SAMPluginCommonSpecPromptKeys.MAXTOKENS.value],
            self.data[SAMKeys.SPEC.value][SAMPluginSpecKeys.PROMPT.value][
                SAMPluginCommonSpecPromptKeys.MAXTOKENS.value
            ],
        )

    def test_plugin_called_signal(self):
        """Test the plugin_called signal."""
        plugin_called.connect(self.plugin_called_signal_handler, dispatch_uid="plugin_called_test_plugin_called_signal")

        plugin = StaticPlugin(data=self.data)
        plugin.function_calling_plugin(inquiry_type="sales_promotions")

        self.assertTrue(self.signals["plugin_called"])

    def test_plugin_selected_signal(self):
        """Test the plugin_selected signal."""
        plugin_selected.connect(
            self.plugin_selected_signal_handler, dispatch_uid="plugin_selected_test_plugin_selected_signal"
        )

        messages = [
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: "you are a helpful chatbot.",
            },
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.USER_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: "have you ever heard of everlasting gobstoppers?",
            },
        ]

        plugin = StaticPlugin(data=self.data)
        plugin.selected(user=self.user, messages=messages)
        self.assertTrue(self.signals["plugin_selected"])

        sleep(1)

        self._plugin_selected = False
        messages = [
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: "you are a helpful chatbot.",
            },
            {
                OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.USER_MESSAGE_KEY,
                OpenAIMessageKeys.MESSAGE_CONTENT_KEY: "this should return false.",
            },
        ]
        self.assertFalse(self.signals["plugin_selected"])
