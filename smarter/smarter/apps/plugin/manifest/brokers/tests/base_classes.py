"""Test base classes for the plugin API tests."""

import os
import unittest

from django.test import Client

from smarter.apps.plugin.tests.base_classes import TestConnectionBase, TestPluginBase

from .factories import create_generic_request


HERE = os.path.abspath(os.path.dirname(__file__))


# pylint: disable=W0223
class TestSAMBrokerMixin(unittest.TestCase):
    """Test SAMStaticPluginBrokerBase"""

    @property
    def good_manifest_path(self) -> str:
        raise NotImplementedError("Subclasses must implement this property")

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_data_path = os.path.join(HERE, "mock_data")
        self.request = create_generic_request()
        self.client = Client()
        self.client.force_login(self.admin_user)

    def tearDown(self):
        """Clean up test fixtures."""
        super().tearDown()

        self.request = None
        self.client = None

    def valid_manifest_self_check(self):
        """
        Test that we can instantiate a valid Plugin manifest without errors.
        This does not need to be exhaustive, as we already have comprehensive tests
        for the manifest itself in smarter.apps.plugin.tests.

        This is intended to be added to setUp() in the child classes:
        def setUp(self):
            super().setUp()
            self.good_manifest_path = os.path.join(self.mock_data_path, "static-plugin-good.yaml")
            self.valid_manifest_self_check()

        """
        self.load_manifest(filename=self.good_manifest_path)
        self.assertIsNotNone(self.model)


class TestSAMPluginBrokerBase(TestPluginBase, TestSAMBrokerMixin):
    """Test SAMStaticPluginBrokerBase"""


class TestSAMConnectionBrokerBase(TestConnectionBase, TestSAMBrokerMixin):
    """Test SAMConnectionBrokerBase"""
