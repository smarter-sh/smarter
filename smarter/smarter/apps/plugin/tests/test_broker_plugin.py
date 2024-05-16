"""Test SAM Plugin Broker"""

import os
import unittest

import yaml

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.plugin.manifest.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.manifest.models.plugin.model import SAMPlugin
from smarter.apps.plugin.manifest.models.sql_connection.model import (
    SAMPluginDataSqlConnection,
)
from smarter.apps.plugin.models import PluginDataSqlConnection
from smarter.lib.django.user import User
from smarter.lib.manifest.loader import SAMLoader

from .factories import plugin_meta_factory


HERE = os.path.abspath(os.path.dirname(__file__))


class TestPluginBroker(unittest.TestCase):
    """Test SAM Plugin Broker"""

    def setUp(self):
        """Set up test fixtures."""
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
        self.connection_loader = SAMLoader(manifest=connection_manifest)
        self.connection_model = SAMPluginDataSqlConnection(**self.connection_loader.pydantic_model_dump())

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
        self.plugin_loader = SAMLoader(manifest=plugin_manifest)

        # 3. create a SAMPlugin pydantic model from the loader
        self.sam_plugin = SAMPlugin(**self.plugin_loader.pydantic_model_dump())

    def tearDown(self):
        """Tear down test fixtures."""
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

    def test_plugin_broker_apply(self):
        """Test that the Broker can apply the manifest."""
        pass
