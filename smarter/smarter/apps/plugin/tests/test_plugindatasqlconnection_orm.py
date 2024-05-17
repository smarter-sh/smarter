"""Test PluginDataSqlConnection Django ORM"""

import os
import unittest

from django.conf import settings
from django.db.backends.base.base import BaseDatabaseWrapper

from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.plugin.manifest.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.manifest.models.sql_connection.const import (
    MANIFEST_KIND as SQL_CONNECTION_KIND,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import (
    SAMPluginDataSqlConnection,
)
from smarter.apps.plugin.models import PluginDataSqlConnection, PluginMeta
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.unittest.utils import get_readonly_yaml_file

from .factories import plugin_meta_factory


HERE = os.path.abspath(os.path.dirname(__file__))


class TestPluginDataSqlConnection(unittest.TestCase):
    """Test PluginDataSqlConnection Django ORM"""

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
        manifest = get_readonly_yaml_file(config_path)

        # 2. initialize a SAMLoader object with the manifest raw data
        self.loader = SAMLoader(manifest=manifest)

        # 3. create a SAMPluginDataSqlConnection pydantic model from the loader
        self.model = SAMPluginDataSqlConnection(**self.loader.pydantic_model_dump())

    def tearDown(self):
        """Tear down test fixtures."""
        try:
            self.meta_data.delete()
        except PluginMeta.DoesNotExist:
            pass
        admin_user_teardown(self.user, self.account, self.user_profile)

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

    def test_manifest(self):
        """Test that the Loader can load the manifest."""
        self.assertEqual(self.loader.manifest_api_version, SAMApiVersions.V1.value)
        self.assertEqual(self.loader.manifest_kind, SQL_CONNECTION_KIND)
        self.assertIsNotNone(self.loader.manifest_metadata)
        self.assertIsNotNone(self.loader.manifest_spec)

    def test_model(self):
        """Test that the Pydantic model populates from the manifest."""
        self.assertIsNotNone(self.model)
        self.assertEqual(self.model.apiVersion, SAMApiVersions.V1.value)
        self.assertEqual(self.model.kind, SQL_CONNECTION_KIND)
        self.assertIsNotNone(self.model.metadata)
        self.assertIsNotNone(self.model.spec)

    def test_django_model(self):
        """Test that the Django model can be initialized from the Pydantic model."""
        model_dump = self.model.spec.connection.model_dump()

        model_dump["account"] = self.account
        model_dump["name"] = self.model.metadata.name
        django_model = PluginDataSqlConnection(**model_dump)
        django_model.save()

        self.assertIsNotNone(django_model)
        self.assertEqual(django_model.account, self.account)
        self.assertEqual(django_model.name, self.model.metadata.name)
        self.assertEqual(django_model.db_engine, self.model.spec.connection.db_engine)
        self.assertEqual(django_model.database, self.model.spec.connection.database)
        self.assertEqual(django_model.hostname, self.model.spec.connection.hostname)
        self.assertEqual(django_model.port, self.model.spec.connection.port)
        self.assertEqual(django_model.username, self.model.spec.connection.username)
        self.assertEqual(django_model.password, self.model.spec.connection.password)

        django_model.delete()

    def test_plugin_datasql_connection_methods(self):
        """use the local dev db settings to Test the Django model properties and built-in functions."""

        cnx = PluginDataSqlConnection(
            account=self.account,
            name="Local Development Database",
            db_engine=settings.DATABASES["default"]["ENGINE"],
            database=settings.DATABASES["default"]["NAME"],
            hostname=settings.DATABASES["default"]["HOST"],
            port=settings.DATABASES["default"]["PORT"],
            username=settings.DATABASES["default"]["USER"],
            password=settings.DATABASES["default"]["PASSWORD"],
        )
        cnx.save()

        self.assertTrue(cnx.validate())

        connection = cnx.connect()
        self.assertIsInstance(connection, BaseDatabaseWrapper)

        result = cnx.execute_query(sql="SELECT count(*) FROM auth_user")
        self.assertIsInstance(result[0][0], int)
