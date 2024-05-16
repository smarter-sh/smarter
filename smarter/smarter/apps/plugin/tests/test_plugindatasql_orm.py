"""Test PluginDataSql Django ORM - validators and sql preparation"""

import os
import unittest

import yaml

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.plugin.manifest.enum import SAMPluginMetadataClassValues
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
    """Test PluginDataSql Django ORM - validators and sql preparation"""

    def setUp(self):
        """Set up test fixtures."""

        self.user, self.account, self.user_profile = admin_user_factory()

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
                },
                "location": {
                    "type": "str",
                    "required": True,
                    "description": "The city and state, e.g., San Francisco, CA",
                },
            },
            sql_query="SELECT * FROM weather WHERE location = '{location}' AND unit = '{unit}'",
            test_values={
                "unit": "Celsius",
                "location": "San Francisco, CA",
            },
            limit=10,
        )
        plugindatasql.save()
        return plugindatasql

    def test_create_PluginDataSql(self):
        """Test create PluginDataSql"""
        plugindatasql = self.plugindatasql_factory()
        plugindatasql.delete()

    def test_PluginDataSql_validate_parameter(self):
        plugindatasql = self.plugindatasql_factory()
        self.assertIsInstance(plugindatasql.data(params=plugindatasql.test_values), dict)

        for _, param in plugindatasql.parameters.items():
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

    def test_PluginDataSql_validate_test_values(self):
        plugindatasql = self.plugindatasql_factory()

        # validate test values, no error means it succeeded
        plugindatasql.validate_test_values()
        test_values = plugindatasql.test_values.copy()

        # test value that is not in the enum list
        bad_test_values = test_values.copy()
        bad_test_values["unit"] = "bad_unit"
        plugindatasql.test_values = bad_test_values
        with self.assertRaises(SmarterValueError):
            plugindatasql.save()
        plugindatasql.delete()

        # test non-existent key
        bad_test_values = test_values.copy()
        bad_test_values["badkey"] = "oops"
        plugindatasql.test_values = bad_test_values
        with self.assertRaises(SmarterValueError):
            plugindatasql.save()

        # test value with type clash
        bad_test_values = test_values.copy()
        bad_test_values["location"] = True
        plugindatasql.test_values = bad_test_values
        with self.assertRaises(SmarterValueError):
            plugindatasql.save()

    def test_PluginDataSql_prepare_sql(self):
        plugindatasql = self.plugindatasql_factory()

        params = {
            "unit": "Celsius",
            "location": "CDMX, Roma Norte",
        }
        sql = plugindatasql.prepare_sql(params)
        self.assertIsInstance(sql, str)
        plugindatasql.delete()
