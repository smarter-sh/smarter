# pylint: disable=wrong-import-position
"""Test SAMUserBroker."""

import logging
import os

from django.http import HttpRequest

from smarter.apps.account.manifest.brokers.user import SAMUserBroker
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


logger = logging.getLogger(__name__)


class TestSmarterUserBroker(TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMUserBroker.
    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    def setUp(self):
        """test-level setup."""
        super().setUp()
        self._broker_class = SAMUserBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("user.yaml")

        if self.loader is None:
            raise RuntimeError("SAMLoader not initialized in base class setup.")
        if self.request is None:
            raise RuntimeError("HttpRequest not initialized in base class setup.")

    def test_setup(self):
        """Verify that setup initialized the broker correctly."""
        self.assertTrue(self.ready())
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.request, HttpRequest)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self._broker, SAMUserBroker)

        logger.info("SAMUserBroker initialized successfully for testing.")
