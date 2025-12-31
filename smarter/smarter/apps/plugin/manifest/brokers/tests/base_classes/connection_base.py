# pylint: disable=wrong-import-position
"""Test TestSmarterConnectionBrokerBase."""


import logging
from datetime import datetime, timedelta

from smarter.apps.account.models import Secret
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


logger = logging.getLogger(__name__)


class TestSmarterConnectionBrokerBase(TestSAMBrokerBaseClass):
    """
    Adds a class-level setup to create Secret instances for use in connection broker tests.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up the test class with a single account, and admin and non-admin users.
        using the class setup so that we retain the same user_profile for each test,
        which is needed so that the django Secret model can be queried.
        """
        super().setUpClass()
        cls.test_secret_name = "smarter"
        cls.test_secret_value = "top-secret-test-password-value"

        expires_at = datetime.now() + timedelta(days=180)  # 6 months from now
        cls.secret = Secret.objects.create(
            user_profile=cls.user_profile,
            name=cls.test_secret_name,
            description=f"Test password secret for SAMConnectionBroker tests. name='{cls.test_secret_name}', value='{cls.test_secret_value}'",
            encrypted_value=Secret.encrypt(cls.test_secret_value),
            expires_at=expires_at,
        )

        cls.test_proxy_secret_name = "smarter-proxy"
        cls.test_proxy_secret_value = "top-secret-proxy-password-value"
        cls.proxy_secret = Secret.objects.create(
            user_profile=cls.user_profile,
            name=cls.test_proxy_secret_name,
            description=f"Test password secret for SAMConnectionBroker tests. name='{cls.test_proxy_secret_name}', value='{cls.test_proxy_secret_value}'",
            encrypted_value=Secret.encrypt(cls.test_proxy_secret_value),
            expires_at=expires_at,
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up the created secret after all tests have run."""
        try:
            cls.secret.delete()
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Error deleting test secret in tearDownClass: %s", e)

        try:
            cls.proxy_secret.delete()
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Error deleting test proxy secret in tearDownClass: %s", e)

        super().tearDownClass()
