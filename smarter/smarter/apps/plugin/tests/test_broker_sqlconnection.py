"""Test SAM PluginDataSqlConnection Broker"""

import json
import os
import unittest
from http import HTTPStatus

import yaml
from django.test import Client

from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.plugin.manifest.brokers.sql_connection import (
    SAMPluginDataSqlConnectionBroker,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import (
    SAMPluginDataSqlConnection,
)
from smarter.common.utils import dict_is_contained_in
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.manifest.broker import SAMBrokerErrorNotImplemented
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.unittest.utils import get_readonly_yaml_file

from .factories import create_generic_request


HERE = os.path.abspath(os.path.dirname(__file__))


class TestSAMPluginDataSqlConnectionBroker(unittest.TestCase):
    """Test SAM PluginDataSqlConnection Broker"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.user, cls.account, cls.user_profile = admin_user_factory()
        cls.client = Client()
        cls.request = create_generic_request()
        cls.kwargs = {}

        config_path = os.path.join(HERE, "mock_data/sql-connection.yaml")
        connection_manifest = get_readonly_yaml_file(config_path)

        cls.broker = SAMPluginDataSqlConnectionBroker(
            request=cls.request, account=cls.account, manifest=connection_manifest
        )

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        admin_user_teardown(cls.user, cls.account, cls.user_profile)

    def test_sqlconnection_broker_apply(self):
        """Test that the Broker can apply the manifest."""
        retval = self.broker.apply(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(
            content["message"],
            f"{SmarterJournalThings.PLUGIN_DATA_SQL_CONNECTION.value} testConnection applied successfully",
        )

    def test_sqlconnection_broker_describe(self):
        """
        Test that the Broker can generate and return a valid manifest.
        - create a resource from a manifest
        - describe the resource
        - convert the description from json to yaml
        - load the yaml description into a SAMLoader object
        - create a pydantic model from the loader
        - dump the pydantic model to a dictionary
        """

        retval = self.broker.apply(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        # generate the manifest
        retval = self.broker.describe(request=self.request, kwargs=self.kwargs)
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
        pydantic_model = SAMPluginDataSqlConnection(**loader.pydantic_model_dump())

        # dump the pydantic model to a dictionary
        round_trip_dict = pydantic_model.model_dump()

        # assert that everything in content is in round_trip_dict
        self.assertTrue(dict_is_contained_in(content, round_trip_dict))

    def test_sqlconnection_broker_delete(self):
        """Test that the Broker can delete the object."""
        retval = self.broker.apply(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        retval = self.broker.delete(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(
            content["message"],
            f"{SmarterJournalThings.PLUGIN_DATA_SQL_CONNECTION.value} testConnection deleted successfully",
        )

    def test_sqlconnection_broker_deploy(self):
        """Test that the Broker does not implement a deploy() method."""

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.deploy(request=self.request, kwargs=self.kwargs)
