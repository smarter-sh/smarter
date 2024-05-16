"""Test SAM Plugin manifest using PluginDataSql"""

import os
import unittest

import yaml

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.plugin.model import SAMPlugin
from smarter.apps.plugin.manifest.models.sql_connection.model import (
    SAMPluginDataSqlConnection,
)
from smarter.apps.plugin.models import PluginDataSqlConnection
from smarter.lib.django.user import User
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.loader import SAMLoader

from .factories import plugin_meta_factory


HERE = os.path.abspath(os.path.dirname(__file__))


class TestPluginDataSql(unittest.TestCase):
    """Test SAM Plugin manifest using PluginDataSql"""

    def setUp(self):
        """Set up test fixtures."""
        # set user, account, user_profile
        # ---------------------------------------------------------------------
        self.user, self.account, self.user_profile = admin_user_factory()
        self.meta_data = plugin_meta_factory(
            plugin_class=SAMPluginMetadataClassValues.SQL.value, account=self.account, user_profile=self.user_profile
        )

        # setup an instance of PluginDataSqlConnection() - a Django model
        # ---------------------------------------------------------------------
        # 1. load the yaml manifest file
        config_path = os.path.join(HERE, "mock_data/sql-connection.yaml")
        with open(config_path, encoding="utf-8") as file:
            connection_manifest = yaml.safe_load(file)

        # 2. initialize a SAMLoader object with the manifest raw data
        self.connection_loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=connection_manifest)

        # 3. create a SAMPluginDataSqlConnection pydantic model from the loader
        self.connection_model = SAMPluginDataSqlConnection(
            apiVersion=self.connection_loader.manifest_api_version,
            kind=self.connection_loader.manifest_kind,
            metadata=self.connection_loader.manifest_metadata,
            spec=self.connection_loader.manifest_spec,
            status=self.connection_loader.manifest_status,
        )

        # 4. create the connection record
        model_dump = self.connection_model.spec.connection.model_dump()
        model_dump["account"] = self.account
        model_dump["name"] = self.connection_model.metadata.name
        self.plugin_datasql_connection = PluginDataSqlConnection(**model_dump)
        self.plugin_datasql_connection.save()

        # setup an instance of PluginSql() - a Python class descended from PluginBase()
        # ---------------------------------------------------------------------
        # 1. load the yaml manifest file
        config_path = os.path.join(HERE, "mock_data/sql-test.yaml")
        with open(config_path, encoding="utf-8") as file:
            plugin_manifest = yaml.safe_load(file)

        # 2. initialize a SAMLoader object with the manifest raw data
        self.plugin_loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=plugin_manifest)

        # 3. create a SAMPlugin pydantic model from the loader
        spec = self.plugin_loader.manifest_spec

        self.sam_plugin = SAMPlugin(
            apiVersion=self.plugin_loader.manifest_api_version,
            kind=self.plugin_loader.manifest_kind,
            metadata=self.plugin_loader.manifest_metadata,
            spec=spec,
            status=self.plugin_loader.manifest_status,
        )

        cnx = self.connection_loader.manifest_spec["connection"]
        cnx["account"] = self.account
        self.connection = PluginDataSqlConnection(**cnx)

        # 4. use the PluginController to resolve which kind of Plugin to instantiate
        controller = PluginController(account=self.account, manifest=self.sam_plugin)
        self.plugin = controller.obj
        self.plugins = [self.plugin]

    def tearDown(self):
        """Tear down test fixtures."""
        try:
            self.plugin_datasql_connection.delete()
        except PluginDataSqlConnection.DoesNotExist:
            pass
        self.plugin.delete()
        try:
            self.connection.delete()
        except (PluginDataSqlConnection.DoesNotExist, ValueError):
            pass
        try:
            self.user_profile.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            self.user.delete()
        except User.DoesNotExist:
            pass
        try:
            self.account.delete()
        except Account.DoesNotExist:
            pass

    def properties_factory(self) -> dict:
        return {
            "properties": {
                "location": {"type": "string", "description": "The city and state, e.g., San Francisco, CA"},
                "unit": {
                    "type": "string",
                    "enum": ["Celsius", "Fahrenheit"],
                    "description": "The temperature unit to use. Infer this from the user's location.",
                },
            },
        }

    def test_plugin_loader(self):
        """Test that the Loader can load the manifest."""
        self.assertEqual(self.plugin_loader.manifest_api_version, SAMApiVersions.V1.value)
        self.assertEqual(self.plugin_loader.manifest_kind, MANIFEST_KIND)
