"""Test PluginDataSql Django ORM - sql execution, self test, and return data sanitization"""

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
from smarter.lib.django.user import User
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TestPluginDataSqlConnection(unittest.TestCase):
    """
    Test PluginDataSql Django ORM - sql execution, self test, and return data sanitization.
    Run tests against the Django ORM for the auth_user model. This is a simple model with a few fields
    that we know to already exist in the database.
    """

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
                "username": {
                    "type": "str",
                    "required": True,
                    "description": "The username of the user",
                },
                "email": {
                    "type": "str",
                    "required": False,
                    "description": "The email address of the user",
                },
                "is_staff": {
                    "type": "bool",
                    "required": False,
                    "description": "whether or not the user is a staff member",
                },
                "is_active": {
                    "type": "bool",
                    "required": False,
                    "description": "whether or not the user account is activated",
                },
            },
            sql_query="SELECT * FROM auth_user WHERE <username>username = '{username}'</username> <email>AND email = '{email}'</email> <is_staff>AND is_staff in {is_staff} = True</is_staff> <is_active>AND {is_active} = True</is_active>",
            test_values={"username": "admin"},
            limit=10,
        )
        plugindatasql.save()
        return plugindatasql

    def test_execute_query(self):
        plugindatasql = self.plugindatasql_factory()
        plugindatasql.delete()

    def test_test(self):
        plugindatasql = self.plugindatasql_factory()
        plugindatasql.test()
        plugindatasql.delete()

    def test_sanitized_return_data(self):
        plugindatasql = self.plugindatasql_factory()
        retval = plugindatasql.sanitized_return_data(
            {
                "username": "admin",
                "is_active": True,
            }
        )
        self.assertIsInstance(retval, tuple)
        plugindatasql.delete()
