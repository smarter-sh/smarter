"""Test lambda_openai_v2 function."""

import hashlib
import os
import random

# python stuff
import sys
import unittest
from pathlib import Path

import yaml

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.manifest.controller import PluginController
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
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402


# pylint: disable=too-many-public-methods,too-many-instance-attributes
class TestOpenaiFunctionCallingSqlData(unittest.TestCase):
    """Test Index Lambda function."""

    def setUp(self):
        """Set up test fixtures."""
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]

        username = f"test_{hashed_slug}"
        self.user = User.objects.create(username=username, password="12345")
        self.account = Account.objects.create(company_name=f"Test_{hashed_slug}", phone_number="123-456-789")
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)

        config_path = os.path.join(HERE, "mock_data/sql-connection.yaml")
        with open(config_path, encoding="utf-8") as file:
            connection_manifest = yaml.safe_load(file)

        config_path = os.path.join(HERE, "mock_data/sql-test.yaml")
        with open(config_path, encoding="utf-8") as file:
            plugin_manifest = yaml.safe_load(file)

        connection_loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=connection_manifest)
        cnx = connection_loader.manifest_spec["connection"]
        cnx["account"] = self.account
        self.connection = PluginDataSqlConnection(**cnx)

        controller = PluginController(account=self.account, manifest=plugin_manifest)
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
