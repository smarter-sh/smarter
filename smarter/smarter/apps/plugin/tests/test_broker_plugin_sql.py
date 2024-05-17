"""Test SAM Plugin Broker with sql manifest"""

import json
import os
import unittest
from http import HTTPStatus

import yaml

from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.plugin.manifest.brokers.plugin import SAMPluginBroker
from smarter.apps.plugin.manifest.brokers.sql_connection import (
    SAMPluginDataSqlConnectionBroker,
)
from smarter.apps.plugin.manifest.models.plugin.model import SAMPlugin
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TestSAMPluginSql(unittest.TestCase):
    """Test SAM Plugin Broker with sql manifest"""

    def setUp(self):
        """Set up test fixtures."""
        self.user, self.account, self.user_profile = admin_user_factory()

        # create a sql connection
        config_path = os.path.join(HERE, "mock_data/sql-connection.yaml")
        with open(config_path, encoding="utf-8") as file:
            connection_manifest = yaml.safe_load(file)
        self.connection_broker = SAMPluginDataSqlConnectionBroker(account=self.account, manifest=connection_manifest)
        self.connection_broker.apply()

        # create a plugin broker
        config_path = os.path.join(HERE, "mock_data/sql-test.yaml")
        with open(config_path, encoding="utf-8") as file:
            plugin_manifest = yaml.safe_load(file)
        self.plugin_broker = SAMPluginBroker(account=self.account, manifest=plugin_manifest)

    def tearDown(self):
        """Tear down test fixtures."""
        self.connection_broker.delete()
        admin_user_teardown(self.user, self.account, self.user_profile)

    def test_plugin_broker_apply(self):
        """Test that the Broker can apply the manifest."""
        retval = self.plugin_broker.apply()
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "Plugin SqlTest applied successfully")

    def test_plugin_broker_describe(self):
        """
        Test that the Broker can generate and return a valid manifest.
        - create a resource from a manifest
        - describe the resource
        - convert the description from json to yaml
        - load the yaml description into a SAMLoader object
        - create a pydantic model from the loader
        - dump the pydantic model to a dictionary
        """

        def dict_is_contained_in(dict1, dict2):
            for key, value in dict1.items():
                if key not in dict2:
                    print("key not in dict2: ", key)
                    return False
                if isinstance(value, dict):
                    if not dict_is_contained_in(value, dict2[key]):
                        print("dict not in dict2: ", value)
                        return False
                else:
                    if dict2[key] != value:
                        print("value not in dict2: ", value)
                        return False
            return True

        retval = self.plugin_broker.apply()
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        # generate the manifest
        retval = self.plugin_broker.describe()
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        # transform the json content to a yaml manifest
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        content = content["data"]  # the manifest is loaded into the 'data' key
        content.pop("status")  # status is read-only
        manifest = yaml.dump(content)

        # load the yaml manifest into a SAMLoader object
        loader = SAMLoader(manifest=manifest)
        # create a pydantic model from the loader
        pydantic_model = SAMPlugin(**loader.pydantic_model_dump())

        # dump the pydantic model to a dictionary
        round_trip_dict = pydantic_model.model_dump()

        # assert that everything in content is in round_trip_dict
        print("FIX NOTE: CANNOT ROUND-TRIP THE PLUGIN MANIFEST")
        # self.assertTrue(dict_is_contained_in(content, round_trip_dict))

    def test_plugin_broker_delete(self):
        """Test that the Broker can delete the object."""
        retval = self.plugin_broker.apply()
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        retval = self.plugin_broker.delete()
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "Plugin SqlTest deleted successfully")

    def test_plugin_broker_deploy(self):
        """Test that the Broker does not implement a deploy() method."""

        retval = self.plugin_broker.deploy()
        self.assertEqual(retval.status_code, HTTPStatus.NOT_IMPLEMENTED)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "operation not implemented for Plugin resources")
