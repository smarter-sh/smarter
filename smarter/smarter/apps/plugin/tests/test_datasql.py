"""Test PluginDataSql class"""

import hashlib
import os
import random
import unittest

import yaml

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.plugin.model import SAMPlugin
from smarter.apps.plugin.manifest.models.sql_connection.model import (
    SAMPluginDataSqlConnection,
)
from smarter.apps.plugin.models import (
    PluginDataSql,
    PluginDataSqlConnection,
    PluginMeta,
)
from smarter.apps.plugin.serializers import (
    PluginDataSqlConnectionSerializer,
    PluginDataSqlSerializer,
)
from smarter.lib.django.user import User
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TestPluginDataSql(unittest.TestCase):
    """Test PluginDataSql class"""

    def setUp(self):
        """Set up test fixtures."""

        # set user, account, user_profile
        # ---------------------------------------------------------------------
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
        username = f"test_{hashed_slug}"
        self.user = User.objects.create(username=username, password="12345")
        self.account = Account.objects.create(company_name=f"Test_{hashed_slug}", phone_number="123-456-789")
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)

        # setup an instance of PluginDataSqlConnection() - a Django model
        # ---------------------------------------------------------------------
        # 1. load the yaml manifest file
        config_path = os.path.join(HERE, "mock_data/sql-connection.yaml")
        with open(config_path, encoding="utf-8") as file:
            connection_manifest = yaml.safe_load(file)

        # 2. initialize a SAMLoader object with the manifest raw data
        connection_loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=connection_manifest)

        # 3. create a SAMPluginDataSqlConnection pydantic model from the loader
        self.sam_connection = SAMPluginDataSqlConnection(
            apiVersion=connection_loader.manifest_api_version,
            kind=connection_loader.manifest_kind,
            metadata=connection_loader.manifest_metadata,
            spec=connection_loader.manifest_spec,
            status=connection_loader.manifest_status,
        )

        # setup an instance of PluginSql() - a Python class descended from PluginBase()
        # ---------------------------------------------------------------------
        # 1. load the yaml manifest file
        config_path = os.path.join(HERE, "mock_data/sql-test.yaml")
        with open(config_path, encoding="utf-8") as file:
            plugin_manifest = yaml.safe_load(file)

        # 2. initialize a SAMLoader object with the manifest raw data
        plugin_loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=plugin_manifest)

        # 3. create a SAMPlugin pydantic model from the loader
        sam_plugin = SAMPlugin(
            apiVersion=plugin_loader.manifest_api_version,
            kind=plugin_loader.manifest_kind,
            metadata=plugin_loader.manifest_metadata,
            spec=plugin_loader.manifest_spec,
            status=plugin_loader.manifest_status,
        )

        cnx = connection_loader.manifest_spec["connection"]
        cnx["account"] = self.account
        self.connection = PluginDataSqlConnection(**cnx)

        # 4. use the PluginController to resolve which kind of Plugin to instantiate
        controller = PluginController(account=self.account, manifest=sam_plugin)
        self.plugin = controller.obj
        self.plugins = [self.plugin]

    def tearDown(self):
        """Tear down test fixtures."""
        self.plugin.delete()
        try:
            self.connection.delete()
        except PluginDataSqlConnection.DoesNotExist:
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

    def plugin_meta_factory(self) -> PluginMeta:
        plugin_meta = PluginMeta(
            account=self.account,
            name="TestPlugin",
            description="Test Plugin",
            version="0.0.1",
            plugin_type="sql",
        )
        plugin_meta.save()
        return plugin_meta

    def sql_connection_factory(self) -> PluginDataSqlConnection:
        connection = PluginDataSqlConnection(
            account=self.account,
            name="TestConnection",
            db_engine="sqlite",
            hostname="localhost",
            port=3306,
            username="root",
            password="password",
            database="test",
        )
        connection.save()
        return connection

    def plugin_data_sql_factory(self, plugin_meta, connection) -> PluginDataSql:
        data_sql = PluginDataSql(
            plugin=plugin_meta,
            connection=connection,
            description="Test Data SQL",
            parameters={},
            sql_query="SELECT * FROM test",
            test_values={},
            limit=10,
        )
        data_sql.save()
        return data_sql

    def test_plugin_data_sql_create(self):
        plugin_meta = self.plugin_meta_factory()
        connection = self.sql_connection_factory()
        data_sql = self.plugin_data_sql_factory(plugin_meta=plugin_meta, connection=connection)

        data_sql.validate()

        sql = data_sql.prepare_sql(params=data_sql.test_values)
        print("sql", sql)

        data_sql.test()
        data_sql.execute_query(data_sql.test_values)

        print(data_sql.sanitized_return_data(params=data_sql.test_values))

        print(data_sql.data(params=data_sql.test_values))

        for param in self.properties_factory():
            data_sql.validate_parameter(param=param)

    def test_sql_data(self):
        """Test sql data."""

        connection_serializer = PluginDataSqlConnectionSerializer(self.connection).data
        plugin_serializer = PluginDataSqlSerializer(self.plugin).data

        print("connection_serializer", connection_serializer)
        print("plugin_serializer", plugin_serializer)

    def test_sql_record(self):
        """Test sql record."""

        data_sql = PluginDataSql.objects.get(plugin=self.plugin.plugin_meta)
        print("data_sql", data_sql)

        data_sql.test()
        print("test_sql: ", data_sql.prepare_sql(params=data_sql.test_values))
