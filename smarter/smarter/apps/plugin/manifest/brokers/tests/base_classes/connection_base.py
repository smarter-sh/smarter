# pylint: disable=wrong-import-position
"""Test TestSmarterConnectionBrokerBase."""


import logging
import os

from smarter.apps.account.const import DATA_PATH as ACCOUNT_DATA_PATH
from smarter.apps.account.models import Secret
from smarter.apps.api.utils import apply_manifest
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


logger = logging.getLogger(__name__)
MANIFEST_PATH_SECRET_SMARTER_TEST_DB_PASSWORD = os.path.abspath(
    os.path.join(ACCOUNT_DATA_PATH, "example-manifests", "secret-smarter-test-db.yaml")
)
"""
Path to the Secret manifest file 'secret-smarter-test-db.yaml' which
contains the actual password value for the remote test database.
"""

MANIFEST_PATH_SECRET_PROXY_PASSWORD = os.path.abspath(
    os.path.join(ACCOUNT_DATA_PATH, "example-manifests", "secret-smarter-test-db-proxy-password.yaml")
)
"""
Path to the Secret manifest file 'secret-smarter-test-db-proxy-password.yaml' which
contains the actual password value for the proxy connection.
"""

HERE = __name__


class TestSmarterConnectionBrokerBase(TestSAMBrokerBaseClass):
    """
    Adds a class-level setup to create Secret instances for use in connection broker tests.
    """

    test_smarter_connection_broker_base_logger_prefix = formatted_text(f"{HERE}.TestSmarterConnectionBrokerBase()")

    @classmethod
    def setUpClass(cls):
        """
        Set up the test class with a single account, and admin and non-admin users.
        using the class setup so that we retain the same user_profile for each test,
        which is needed so that the django Secret model can be queried.

        # note: this is SMARTER_MYSQL_TEST_DATABASE_PASSWORD from .env
        # cls.test_secret_value = smarter_settings.smarter_mysql_test_database_password.get_secret_value()

        # note: this is SMARTER_MYSQL_TEST_DATABASE_PASSWORD from .env
        # cls.test_proxy_secret_value = smarter_settings.smarter_mysql_test_database_password.get_secret_value()
        """
        super().setUpClass()
        logger.debug("%s.setUpClass()", cls.test_smarter_connection_broker_base_logger_prefix)
        test_secret_loader = SAMLoader(file_path=MANIFEST_PATH_SECRET_SMARTER_TEST_DB_PASSWORD)
        apply_manifest(username=cls.admin_user.username, manifest=test_secret_loader.yaml_data, verbose=True)

        # this should match spec.connection.password in ../data/sql-connection.yaml
        # assumed to be: smarter_test_user
        cls.test_secret_name = test_secret_loader.manifest_metadata.get("name")
        if not cls.test_secret_name:
            raise SmarterValueError("Failed to get test secret name from manifest metadata.")
        try:
            cls.secret = Secret.objects.get(
                user_profile=cls.user_profile,
                name=cls.test_secret_name,
            )
            cls.test_secret_value = cls.secret.get_secret()
        except Secret.DoesNotExist as e:
            raise SmarterValueError(f"Failed to get test secret '{cls.test_secret_name}' from database.") from e
        logger.debug(
            "%s.setUpClass() %s owned by %s created for connection broker tests.",
            cls.test_smarter_connection_broker_base_logger_prefix,
            cls.test_secret_name,
            cls.user_profile,
        )

        test_proxy_secret_loader = SAMLoader(file_path=MANIFEST_PATH_SECRET_PROXY_PASSWORD)
        apply_manifest(username=cls.admin_user.username, manifest=test_proxy_secret_loader.yaml_data, verbose=True)

        # this should match spec.connection.proxyPassword
        # in ../data/sql-connection.yaml. if the parameter
        # is not set in the manifest then proxy connection will not be tested.
        cls.test_proxy_secret_name = test_proxy_secret_loader.manifest_metadata.get("name")
        if not cls.test_proxy_secret_name:
            raise SmarterValueError("Failed to get test proxy secret name from manifest metadata.")

        try:
            cls.proxy_secret = Secret.objects.get(
                user_profile=cls.user_profile,
                name=cls.test_proxy_secret_name,
            )
            cls.test_proxy_secret_value = cls.proxy_secret.get_secret()
        except Secret.DoesNotExist as e:
            raise SmarterValueError(
                f"Failed to get test proxy secret '{cls.test_proxy_secret_name}' from database."
            ) from e

        logger.debug(
            "%s.setUpClass() %s owned by %s created for connection broker tests.",
            cls.test_smarter_connection_broker_base_logger_prefix,
            cls.test_proxy_secret_name,
            cls.user_profile,
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up the created secret after all tests have run."""
        logger.debug("%s.tearDownClass()", cls.test_smarter_connection_broker_base_logger_prefix)
        try:
            cls.secret.delete()
            logger.debug(
                "%s.tearDownClass() Test secret %s owned by %s deleted after connection broker tests.",
                cls.test_smarter_connection_broker_base_logger_prefix,
                cls.test_secret_name,
                cls.user_profile,
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.tearDownClass() Error deleting test secret %s owned by %s: %s",
                cls.test_smarter_connection_broker_base_logger_prefix,
                cls.test_secret_name,
                cls.user_profile,
                str(e),
            )

        try:
            cls.proxy_secret.delete()
            logger.debug(
                "%s.tearDownClass() Test proxy secret %s owned by %s deleted after connection broker tests.",
                cls.test_smarter_connection_broker_base_logger_prefix,
                cls.test_proxy_secret_name,
                cls.user_profile,
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.tearDownClass() Error deleting test proxy secret %s owned by %s: %s",
                cls.test_smarter_connection_broker_base_logger_prefix,
                cls.test_proxy_secret_name,
                cls.user_profile,
                str(e),
            )

        super().tearDownClass()
