"""Test PluginDataSql Django ORM"""

import hashlib
import os
import random
import unittest

import yaml

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.manifest.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.manifest.models.sql_connection.const import (
    MANIFEST_KIND as SQL_CONNECTION_KIND,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import (
    SAMPluginDataSqlConnection,
)
from smarter.apps.plugin.models import (
    PluginDataSql,
    PluginDataSqlConnection,
    PluginMeta,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.user import User
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TestPluginDataSqlConnection(unittest.TestCase):
    """Test PluginDataSql Django ORM"""

    def setUp(self):
        """Set up test fixtures."""

        # set user, account, user_profile
        # ---------------------------------------------------------------------
        hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
        username = f"test_{hashed_slug}"
        self.user = User.objects.create(username=username, password="12345")
        self.account = Account.objects.create(company_name=f"Test_{hashed_slug}", phone_number="123-456-789")
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)

        self.meta_data = PluginMeta(
            account=self.account,
            name="Test Plugin",
            description="Test Plugin Description",
            plugin_class=SAMPluginMetadataClassValues.SQL.value,
            version="1.0.0",
            author=self.user_profile,
        )
        self.meta_data.save()

        # setup an instance of PluginDataSqlConnection() - a Django model
        # ---------------------------------------------------------------------
        # 1. load the yaml manifest file
        config_path = os.path.join(HERE, "mock_data/sql-connection.yaml")
        with open(config_path, encoding="utf-8") as file:
            manifest = yaml.safe_load(file)

        # 2. initialize a SAMLoader object with the manifest raw data
        self.loader = SAMLoader(api_version=SAMApiVersions.V1.value, manifest=manifest)

        # 3. create a SAMPluginDataSqlConnection pydantic model from the loader
        self.model = SAMPluginDataSqlConnection(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=self.loader.manifest_metadata,
            spec=self.loader.manifest_spec,
            status=self.loader.manifest_status,
        )

        model_dump = self.model.spec.connection.model_dump()
        model_dump["account"] = self.account
        model_dump["name"] = self.model.metadata.name
        self.plugindata_sqlconnection = PluginDataSqlConnection(**model_dump)
        self.plugindata_sqlconnection.save()

    def tearDown(self):
        """Tear down test fixtures."""
        try:
            self.plugindata_sqlconnection.delete()
        except PluginDataSqlConnection.DoesNotExist:
            pass
        try:
            self.meta_data.delete()
        except PluginMeta.DoesNotExist:
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

    def plugindatasql_factory(self) -> PluginDataSql:
        plugindatasql = PluginDataSql(
            plugin=self.meta_data,
            connection=self.plugindata_sqlconnection,
            parameters={
                "unit": {
                    "type": "str",
                    "enum": ["Celsius", "Fahrenheit"],
                    "required": True,
                    "description": "The temperature unit to use. Infer this from the user location.",
                }
            },
            sql_query="SELECT * FROM weather WHERE location = {location} AND unit = {unit}",
            test_values={},
            limit=10,
        )
        plugindatasql.save()
        return plugindatasql

    def test_create_PluginDataSql(self):
        """Test create PluginDataSql"""
        plugindatasql = self.plugindatasql_factory()
        plugindatasql.delete()

    def test_PluginDataSql_methods(self):
        plugindatasql = self.plugindatasql_factory()
        self.assertIsInstance(plugindatasql.data(params=plugindatasql.parameters), dict)

        # {'type': 'str', 'enum': ['Celsius', 'Fahrenheit'], 'required': True, 'description': 'The temperature unit to use. Infer this from the user location.'}
        for _, param in plugindatasql.parameters.items():
            print("param value: ", param)

            # validate parameter, no error means it succeeded
            plugindatasql.validate_parameter(param=param)

            bad_param = param.copy()
            bad_param["type"] = "bad_type"
            with self.assertRaises(SmarterValueError):
                plugindatasql.validate_parameter(param=bad_param)

            bad_param = param.copy()
            bad_param["enum"] = "bad_enum"
            with self.assertRaises(SmarterValueError):
                plugindatasql.validate_parameter(param=bad_param)

            bad_param = param.copy()
            bad_param["required"] = "bad_required"
            with self.assertRaises(SmarterValueError):
                plugindatasql.validate_parameter(param=bad_param)

        plugindatasql.delete()
