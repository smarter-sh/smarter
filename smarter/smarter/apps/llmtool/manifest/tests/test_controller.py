"""Test Plugin manifest controller."""

from smarter.apps.llmtool.manifest.controller import PluginController
from smarter.apps.llmtool.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.llmtool.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.llmtool.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.llmtool.tests.base_classes import TestPluginClassBase


class TestPluginController(TestPluginClassBase):
    """Test Plugin manifest controller."""

    def test_controller_static_plugin(self):
        """Test valid file path and that we can instantiate without errors."""
        self.load_manifest(filename="static-plugin.yaml")
        if not self.loader:
            self.fail("Loader is None")

        model = SAMStaticPlugin(**self.loader.pydantic_model_dump())
        self.assertIsInstance(model, SAMStaticPlugin)

        controller = PluginController(user_profile=self.user_profile, manifest=model)
        self.assertIsInstance(controller, PluginController)

    def test_controller_api_plugin(self):
        """Test valid file path and that we can instantiate without errors."""
        self.load_manifest(filename="api-plugin.yaml")
        if not self.loader:
            self.fail("Loader is None")

        model = SAMApiPlugin(**self.loader.pydantic_model_dump())
        self.assertIsInstance(model, SAMApiPlugin)

        controller = PluginController(user_profile=self.user_profile, manifest=model)
        self.assertIsInstance(controller, PluginController)

    def test_controller_sql_plugin(self):
        """Test valid file path and that we can instantiate without errors."""
        self.load_manifest(filename="sql-plugin.yaml")
        if not self.loader:
            self.fail("Loader is None")

        model = SAMSqlPlugin(**self.loader.pydantic_model_dump())
        self.assertIsInstance(model, SAMSqlPlugin)

        controller = PluginController(user_profile=self.user_profile, manifest=model)
        self.assertIsInstance(controller, PluginController)
