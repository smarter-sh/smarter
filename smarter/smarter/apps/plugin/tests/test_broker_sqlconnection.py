"""Test SAM PluginDataSqlConnection Broker"""

import json
import os
import unittest
from http import HTTPStatus

import yaml

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.plugin.manifest.brokers.sql_connection import (
    SAMPluginDataSqlConnectionBroker,
)
from smarter.lib.django.user import User


HERE = os.path.abspath(os.path.dirname(__file__))


class TestSAMPluginDataSqlConnectionBroker(unittest.TestCase):
    """Test SAM PluginDataSqlConnection Broker"""

    def setUp(self):
        """Set up test fixtures."""
        self.user, self.account, self.user_profile = admin_user_factory()

        config_path = os.path.join(HERE, "mock_data/sql-connection.yaml")
        with open(config_path, encoding="utf-8") as file:
            connection_manifest = yaml.safe_load(file)

        self.broker = SAMPluginDataSqlConnectionBroker(
            account=self.account, user=self.user, user_profile=self.user_profile, manifest=connection_manifest
        )

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
        retval = self.broker.apply()
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "PluginDataSqlConnection testConnection applied successfully")
