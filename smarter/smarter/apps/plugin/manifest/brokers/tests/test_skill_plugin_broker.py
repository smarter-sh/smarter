# pylint: disable=wrong-import-position
"""Test SAMSkillPluginBroker."""

import os

from django.http import HttpRequest
from pydantic_core import ValidationError

from smarter.apps.plugin.manifest.brokers.skill_plugin import SAMSkillPluginBroker
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.skill_plugin.model import SAMSkillPlugin
from smarter.apps.plugin.manifest.models.skill_plugin.spec import SAMSkillPluginSpec
from smarter.apps.plugin.models import PluginDataSkill, PluginMeta
from smarter.apps.plugin.plugin.skill import SkillPlugin
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

from .base_classes.edge_cases import PluginBrokerEdgeCasesMixin

logger = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class TestSmarterSkillPluginBroker(PluginBrokerEdgeCasesMixin, TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMSkillPluginBroker, using a manifest that contains its SKILL.md verbatim.

    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    plugin_class = SkillPlugin
    broker_module = "smarter.apps.plugin.manifest.brokers.skill_plugin"
    spec_kind = "skill"

    def setUp(self):
        super().setUp()
        self._broker_class = SAMSkillPluginBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("skill-plugin.yaml")

    @property
    def ready(self) -> bool:
        if not super().ready:
            return False
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)
        return True

    @property
    def SAMBrokerClass(self) -> type[SAMSkillPluginBroker]:
        return SAMSkillPluginBroker

    @property
    def broker(self) -> SAMSkillPluginBroker:
        return super().broker  # type: ignore

    def test_setup(self):
        """Test that the test setup is correct."""
        self.assertTrue(self.ready)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMSkillPluginBroker)

    def test_is_valid(self):
        """Test that the is_valid property returns True."""
        self.assertTrue(self.broker.is_valid)

    def test_immutability(self):
        """Test that the Pydantic manifest models are immutable."""
        with self.assertRaises(AttributeError):
            self.broker.kind = "NewKind"
        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.name = "NewManifestName"
        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.skillData.skill = "---\nname: x\ndescription: y\n---\n"

    def test_sam_broker_initialization(self):
        """Test that the SAMSkillPlugin model can be initialized from the manifest data."""
        SAMSkillPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
            spec=SAMSkillPluginSpec(**self.loader.manifest_spec),
        )

    def test_broker_initialization(self):
        """Test the broker kind and ORM model class."""
        broker: SAMSkillPluginBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMSkillPluginBroker)
        self.assertEqual(broker.kind, "SkillPlugin")
        self.assertIs(broker.ORMModelClass, PluginDataSkill)
        self.assertIs(broker.SAMModelClass, SAMSkillPlugin)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """Test that the broker can serialize itself to JSON."""
        self.assertIsInstance(json.loads(json.dumps(self.broker.to_json())), dict)

    def test_manifest_initialization(self):
        """Test that the broker can be initialized from a manifest."""
        self.assertIsInstance(self.SAMBrokerClass(self.request, self.broker.manifest), SAMSkillPluginBroker)

    def test_manifest_model_initialization(self):
        """Test that a SAMSkillPlugin can be initialized from a dump of the manifest model."""
        self.assertIsInstance(SAMSkillPlugin(**self.broker.manifest.model_dump()), SAMSkillPlugin)

    def test_formatted_class_name(self):
        """Test the formatted class name."""
        self.assertIn("SAMSkillPluginBroker", self.broker.formatted_class_name)

    def test_manifest_property(self):
        """Test that the manifest property returns a SAMSkillPlugin, whose SKILL.md is verbatim."""
        manifest = self.broker.manifest
        self.assertIsInstance(manifest, SAMSkillPlugin)
        self.assertEqual(manifest.spec.skillData.skill, self.loader.manifest_spec["skillData"]["skill"])

    def test_example_manifest(self):
        """Test the example_manifest() generates a valid manifest response."""
        response = self.broker.example_manifest(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_example_manifest(response))
        data = json.loads(response.content)["data"]
        self.assertIsInstance(SAMSkillPlugin(**data), SAMSkillPlugin)

    def test_get(self):
        """Test the get() method returns a valid manifest response."""
        response = self.broker.get(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_get(response))

    def test_apply(self):
        """Test that apply() stores the verbatim SKILL.md and its bundled files."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(self.validate_apply(response))
        plugin_data = self.broker.plugin.plugin_data
        self.assertIsInstance(plugin_data, PluginDataSkill)
        self.assertEqual(plugin_data.skill_document, self.broker.manifest.spec.skillData.skill)
        self.assertEqual(set(plugin_data.resources), set(self.broker.manifest.spec.skillData.resources or {}))
        self.assertEqual(self.broker.manifest.spec.selector.directive, self.broker.plugin.plugin_selector.directive)
        self.assertEqual(self.broker.manifest.spec.prompt.model, self.broker.plugin.plugin_prompt.model)

    def test_apply_then_describe(self):
        """Test that describe() renders an applied plugin as the manifest author wrote it."""
        self.broker.apply(self.request, **self.kwargs)
        broker = self.SAMBrokerClass(self.request, name=self.broker.manifest.metadata.name)
        spec = broker.plugin_skill_spec_orm2pydantic()
        self.assertIsInstance(spec, SAMSkillPluginSpec)
        self.assertEqual(spec.skillData.skill, self.loader.manifest_spec["skillData"]["skill"])

        response = self.broker.describe(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        data = json.loads(response.content)["data"]
        self.assertEqual(data["spec"]["skillData"]["skill"], self.loader.manifest_spec["skillData"]["skill"])

    def test_plugin(self):
        """Test that the plugin property returns a ready SkillPlugin."""
        plugin = self.broker.plugin
        self.assertIsInstance(plugin, SkillPlugin)
        self.assertTrue(plugin.ready)

    def test_describe(self):
        """Test the describe() method returns a valid manifest response."""
        response = self.broker.describe(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))

    def test_delete(self):
        """Test that delete() removes an applied plugin."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        name = self.broker.manifest.metadata.name
        broker = self.SAMBrokerClass(self.request, self.loader)
        response = broker.delete(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertFalse(PluginMeta.objects.filter(user_profile=self.user_profile, name=name).exists())

    def test_deploy(self):
        """Test that deploy() is not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.deploy(self.request, **self.kwargs)

    def test_undeploy(self):
        """Test that undeploy() is not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.undeploy(self.request, **self.kwargs)

    def test_chat_not_implemented(self):
        """Test that prompt() is not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.prompt(self.request, **self.kwargs)

    def test_logs(self):
        """Test that logs() is not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.logs(self.request, **self.kwargs)
