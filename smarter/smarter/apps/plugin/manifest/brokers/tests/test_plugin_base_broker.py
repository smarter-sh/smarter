"""Test SAMPluginBaseBroker's ORM lookups and ORM-to-Pydantic conversions when their plugin, metadata, prompt or selector is missing, through SAMStaticPluginBroker."""

import os
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.apps.plugin.manifest.brokers import SAMPluginBrokerError
from smarter.apps.plugin.manifest.brokers.plugin_base import SAMPluginBaseBroker
from smarter.apps.plugin.manifest.brokers.static_plugin import SAMStaticPluginBroker
from smarter.apps.plugin.models import PluginDataBase, PluginMeta, PluginSelector
from smarter.lib.manifest.broker import SAMBrokerError
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

MODULE = "smarter.apps.plugin.manifest.brokers.plugin_base"


class TestPluginBaseBroker(TestSAMBrokerBaseClass):
    """Test the SAMPluginBaseBroker branches that a missing plugin, PluginMeta, prompt or selector reach."""

    def setUp(self):
        super().setUp()
        self._broker_class = SAMStaticPluginBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("static-plugin.yaml")

    @property
    def SAMBrokerClass(self) -> type[SAMStaticPluginBroker]:
        return SAMStaticPluginBroker

    @property
    def broker(self) -> SAMStaticPluginBroker:
        return super().broker  # type: ignore

    def patch_property(self, name: str, value) -> PropertyMock:
        patcher = patch.object(SAMStaticPluginBroker, name, new_callable=PropertyMock, return_value=value)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def plugin_meta(self) -> MagicMock:
        plugin_meta = MagicMock(spec=PluginMeta)
        plugin_meta.name = "missing_plugin"
        return plugin_meta

    def test_orm_instance_needs_a_name_and_user_profile(self):
        """There's no ORM instance without a name or a user profile."""
        broker = self.broker
        broker._orm_instance = None
        self.patch_property("name", None)
        self.assertIsNone(broker.orm_instance)
        self.patch_property("name", "missing_plugin")
        self.patch_property("user_profile", None)
        self.assertIsNone(broker.orm_instance)

    def test_orm_instance_not_found_anywhere(self):
        """A plugin that isn't the user's, the account admin's or the platform's has no ORM instance."""
        broker = self.broker
        broker._orm_instance = None
        self.patch_property("name", f"missing_plugin_{self.hash_suffix}")
        self.patch_property("plugin_meta", self.plugin_meta())
        with patch.object(PluginDataBase.objects, "get", side_effect=PluginDataBase.DoesNotExist):
            self.assertIsNone(broker.orm_instance)

    def test_orm_instance_unexpected_error(self):
        """An unexpected error looking up the ORM instance is logged, and there's no instance."""
        broker = self.broker
        broker._orm_instance = None
        self.patch_property("plugin_meta", self.plugin_meta())
        with patch.object(PluginDataBase.objects, "get", side_effect=RuntimeError("database down")):
            self.assertIsNone(broker.orm_instance)

    def test_without_plugin_meta(self):
        """Without a PluginMeta, there are no dependencies, status or prompt, and the conversions raise."""
        broker = self.broker
        self.patch_property("plugin_meta", None)
        broker._plugin_meta = None
        broker._plugin_status = None
        broker._plugin_prompt = None
        self.assertEqual(broker.dependencies(), [])
        self.assertIsNone(broker.plugin_status_pydantic())
        self.assertIsNone(broker.plugin_prompt_orm)
        with self.assertRaises(SAMPluginBrokerError):
            broker.plugin_metadata_orm2pydantic()
        with self.assertRaises(SAMPluginBrokerError):
            broker.plugin_prompt_orm2pydantic()
        with self.assertRaises(SAMPluginBrokerError):
            broker.plugin_selector_orm2pydantic()

    def test_without_a_plugin(self):
        """Without a plugin, the conversions raise."""
        broker = self.broker
        self.patch_property("plugin_meta", self.plugin_meta())
        self.patch_property("plugin", None)
        broker._plugin_meta = self.plugin_meta()
        for conversion in (
            broker.plugin_metadata_orm2pydantic,
            broker.plugin_data_orm2pydantic,
            broker.plugin_prompt_orm2pydantic,
            broker.plugin_selector_orm2pydantic,
        ):
            with self.subTest(conversion=conversion.__name__), self.assertRaises(SAMPluginBrokerError):
                conversion()

    def test_without_plugin_data_or_prompt(self):
        """Without plugin data or a prompt, their conversions raise."""
        broker = self.broker
        self.patch_property("plugin_meta", self.plugin_meta())
        self.patch_property("plugin", MagicMock())
        self.patch_property("plugin_data", None)
        self.patch_property("plugin_prompt_orm", None)
        with self.assertRaises(SAMPluginBrokerError):
            broker.plugin_data_orm2pydantic()
        with self.assertRaises(SAMPluginBrokerError):
            broker.plugin_prompt_orm2pydantic()

    def test_selector_not_found(self):
        """A missing PluginSelector raises."""
        broker = self.broker
        self.patch_property("plugin_meta", self.plugin_meta())
        self.patch_property("plugin", MagicMock())
        with patch.object(PluginSelector, "get_cached_selector_by_plugin", side_effect=PluginSelector.DoesNotExist):
            with self.assertRaises(SAMPluginBrokerError):
                broker.plugin_selector_orm2pydantic()

    def test_cached_plugin_status(self):
        """A cached plugin status is returned as is."""
        broker = self.broker
        status = MagicMock()
        broker._plugin_status = status
        self.assertIs(broker.plugin_status_pydantic(), status)

    def test_base_class_members(self):
        """Plugin_init() resets the broker, unsetting plugin_meta clears it, and plugin_data is abstract."""
        broker = self.broker
        SAMPluginBaseBroker.plugin_init(broker)
        self.assertIsNone(broker._plugin)
        self.assertIsNone(broker._manifest)
        broker.plugin_meta = None  # type: ignore[assignment]
        self.assertIsNone(broker._plugin_meta)
        with self.assertRaises(NotImplementedError):
            SAMPluginBaseBroker.plugin_data.fget(broker)  # type: ignore[attr-defined]

    def test_orm_instance_admin_fallback_errors(self):
        """An unexpected error in the account admin's, or the platform admin's, lookup is logged, and there's no instance."""
        broker = self.broker
        self.patch_property("plugin_meta", self.plugin_meta())
        not_found = PluginDataBase.DoesNotExist
        for side_effect in ([not_found, RuntimeError("down")], [not_found, not_found, RuntimeError("down")]):
            with self.subTest(side_effect=side_effect):
                broker._orm_instance = None
                with (
                    patch.object(PluginMeta.objects, "get", return_value=self.plugin_meta()),
                    patch.object(PluginDataBase.objects, "get", side_effect=side_effect),
                ):
                    self.assertIsNone(broker.orm_instance)

    def test_orm_instance_found_for_platform_admin(self):
        """A plugin that only the platform admin has is found."""
        broker = self.broker
        broker._orm_instance = None
        self.patch_property("plugin_meta", self.plugin_meta())
        orm_instance = MagicMock(spec=PluginDataBase)
        not_found = PluginDataBase.DoesNotExist
        with (
            patch.object(PluginMeta.objects, "get", return_value=self.plugin_meta()),
            patch.object(PluginDataBase.objects, "get", side_effect=[not_found, not_found, orm_instance]),
        ):
            broker.orm_instance  # pylint: disable=pointless-statement
        self.assertIs(broker._orm_instance, orm_instance)

    def test_base_class_plugin(self):
        """The base class's plugin property needs a user and a user profile, then asks the PluginController."""
        broker = self.broker
        plugin = SAMPluginBaseBroker.plugin.fget  # type: ignore[attr-defined]

        broker._plugin = None
        self.patch_property("user", None)
        with self.assertRaises(SAMBrokerError):
            plugin(broker)
        patch.stopall()

        broker._plugin = None
        self.patch_property("user_profile", None)
        with self.assertRaises(SAMBrokerError):
            plugin(broker)
        patch.stopall()

        for obj in (None, MagicMock()):
            with self.subTest(obj=obj):
                broker._plugin = None
                broker._manifest = None
                with patch(f"{MODULE}.PluginController") as controller:
                    controller.return_value.obj = obj
                    self.assertIs(plugin(broker), obj)
                self.assertEqual(controller.call_args.kwargs["manifest"], broker.loader.json_data)

        broker._plugin = "cached"  # type: ignore[assignment]
        self.assertEqual(plugin(broker), "cached")
        broker._plugin = None

    def test_base_class_formatted_class_name(self):
        self.assertIn("SAMPluginBaseBroker", SAMPluginBaseBroker.formatted_class_name.fget(self.broker))  # type: ignore[attr-defined]
