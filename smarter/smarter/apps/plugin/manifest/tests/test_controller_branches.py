"""Test the validation and fallback branches of the Plugin manifest controller."""

from unittest.mock import MagicMock, patch

from django.core.exceptions import MultipleObjectsReturned

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.plugin.manifest.controller import (
    PluginController,
    SAMPluginControllerError,
)
from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.apps.plugin.models import PluginMeta

MODULE = "smarter.apps.plugin.manifest.controller"


def fake_manifest(kind: str = "ApiPlugin", name: str = "fake_plugin") -> MagicMock:
    """A stand-in for a SAM plugin manifest, which passes the controller's isinstance() checks."""
    manifest = MagicMock(spec=SAMPluginCommon)
    manifest.kind = kind
    manifest.metadata = MagicMock()
    manifest.metadata.name = name
    return manifest


class TestPluginControllerBranches(TestAccountMixin):
    """Test PluginController validation, lookups and serialization fallbacks."""

    def test_one_and_only_one_source_is_required(self):
        with self.assertRaises(SAMPluginControllerError):
            PluginController(user_profile=self.user_profile)
        with self.assertRaises(SAMPluginControllerError):
            PluginController(user_profile=self.user_profile, manifest=fake_manifest(), plugin_meta=PluginMeta())

    def test_invalid_manifests_are_rejected(self):
        for manifest in (
            ["not", "a", "manifest"],
            {"metadata": {}},
            {"kind": "NotAPlugin"},
            fake_manifest(kind="NotAPlugin"),
        ):
            with self.subTest(manifest=manifest):
                with self.assertRaises(SAMPluginControllerError):
                    PluginController(user_profile=self.user_profile, manifest=manifest)

    def test_name_only(self):
        """A controller made from a name alone has no manifest, plugin class, plugin or serialization."""
        controller = PluginController(user_profile=self.user_profile, name="fake_plugin")
        self.assertEqual(controller.name, "fake_plugin")
        self.assertIsNone(controller.plugin_class)
        self.assertIsNone(controller.plugin)
        self.assertIsNone(controller.model_dump_json())
        self.assertEqual(controller.get_model_titles(), [])

    def test_unknown_kind_has_no_plugin_class(self):
        controller = PluginController(user_profile=self.user_profile, name="fake_plugin")
        controller._manifest = fake_manifest(kind="NotAPlugin")
        self.assertIsNone(controller.plugin_class)

    def test_plugin_meta_of_another_owner_is_ignored(self):
        fake_model = MagicMock()
        fake_model.DoesNotExist = PluginMeta.DoesNotExist
        fake_model.objects.get.return_value = MagicMock(user_profile=MagicMock())
        controller = PluginController(user_profile=self.user_profile, manifest=fake_manifest())
        with (
            patch(f"{MODULE}.PluginMeta", fake_model),
            patch(f"{MODULE}.valid_resource_owners_for_user", return_value=[]),
        ):
            self.assertIsNone(controller.plugin_meta)

    def test_plugin_meta_lookup_retries_multiple_objects(self):
        found = MagicMock()
        fake_model = MagicMock()
        fake_model.DoesNotExist = PluginMeta.DoesNotExist
        fake_model.objects.get.side_effect = [MultipleObjectsReturned(), found]
        controller = PluginController(user_profile=self.user_profile, manifest=fake_manifest())
        with patch(f"{MODULE}.PluginMeta", fake_model):
            self.assertIs(controller.plugin_meta, found)

    def test_unsupported_plugin_meta_class(self):
        controller = PluginController(user_profile=self.user_profile, plugin_meta=PluginMeta(plugin_class="nope"))
        with self.assertRaises(SAMPluginControllerError):
            _ = controller.obj

    def test_plugin_that_is_a_manifest_provides_the_manifest(self):
        plugin = MagicMock(spec=SAMPluginCommon)
        plugin.manifest = fake_manifest()
        controller = PluginController(user_profile=self.user_profile, plugin_meta=PluginMeta(plugin_class="fake"))
        controller.__dict__["plugin_meta_class_map"] = {"fake": MagicMock(return_value=plugin)}
        self.assertIs(controller.obj, plugin)
        self.assertIs(controller.manifest, plugin.manifest)

    def test_serialization_of_a_plugin(self):
        controller = PluginController(user_profile=self.user_profile, name="fake_plugin")
        controller._plugin = MagicMock()
        controller._plugin.manifest.model_dump_json.return_value = '{"kind": "ApiPlugin"}'
        controller._plugin.manifest.__annotations__ = {"kind": str}
        self.assertEqual(controller.model_dump_json(), {"kind": "ApiPlugin"})
        self.assertEqual(controller.get_model_titles(), [{"name": "kind", "type": str(str)}])
