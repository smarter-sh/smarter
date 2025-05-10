"""Test Plugin manifest controller"""

from typing import Union

from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.tests.base_classes import TestPluginClassBase


class TestPluginController(TestPluginClassBase):
    """Test Plugin manifest controller"""

    model: Union[SAMApiPlugin, SAMSqlPlugin, SAMStaticPlugin] = None

    def setUp(self):
        super().setUp()
        self.model = None

    def tearDown(self):
        super().tearDown()
        self.model = None

    def test_controller_static_plugin(self):
        """
        Test valid file path and that we can instantiate without errors
        """
        self.load_manifest(filename="static-plugin.yaml")
        if not self.loader:
            self.fail("Loader is None")

        self.model = SAMStaticPlugin(**self.loader.pydantic_model_dump())
        self.assertIsInstance(self.model, SAMStaticPlugin)

        controller = PluginController(account=self.account, manifest=self.manifest)
        self.assertIsInstance(controller, PluginController)

    def test_controller_api_plugin(self):
        """
        Test valid file path and that we can instantiate without errors
        """
        self.load_manifest(filename="api-plugin.yaml")
        if not self.loader:
            self.fail("Loader is None")

        self.model = SAMApiPlugin(**self.loader.pydantic_model_dump())
        self.assertIsInstance(self.model, SAMApiPlugin)

        controller = PluginController(account=self.account, manifest=self.manifest)
        self.assertIsInstance(controller, PluginController)

    def test_controller_sql_plugin(self):
        """
        Test valid file path and that we can instantiate without errors
        """
        self.load_manifest(filename="sql-plugin.yaml")
        if not self.loader:
            self.fail("Loader is None")

        self.model = SAMSqlPlugin(**self.loader.pydantic_model_dump())
        self.assertIsInstance(self.model, SAMSqlPlugin)

        controller = PluginController(account=self.account, manifest=self.manifest)
        self.assertIsInstance(controller, PluginController)
