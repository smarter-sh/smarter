# pylint: disable=wrong-import-position
"""Test TestSmarterPluginBrokerBase."""

import logging
import os

from smarter.apps.api.utils import apply_manifest
from smarter.apps.plugin.const import DATA_PATH as PLUGIN_DATA_PATH
from smarter.apps.plugin.models import SqlConnection
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.manifest.loader import SAMLoader

from .connection_base import TestSmarterConnectionBrokerBase

logger = logging.getLogger(__name__)
MANIFEST_PATH_SQL_CONNECTION = os.path.abspath(
    os.path.join(PLUGIN_DATA_PATH, "manifest", "brokers", "tests", "data", "sql-connection.yaml")
)
"""
Path to the Sql connection manifest file 'sql-connection.yaml' which
contains the actual connection parameters for the remote test database.
"""

HERE = __name__


class TestSmarterPluginBrokerBase(TestSmarterConnectionBrokerBase):
    """
    Adds a class-level setup to create SqlConnection instances for use in plugin broker tests.
    """

    test_smarter_plugin_broker_base_logger_prefix = formatted_text(f"{HERE}.TestSmarterPluginBrokerBase()")

    @classmethod
    def setUpClass(cls):
        """
        Set up the test class with:
        - a single account, and admin and non-admin users.
          using the class setup so that we retain the same user_profile for each test
        - a Secret with the Sql connection authentication data
        - create a test SqlConnection from manifest data

        These collectively are the prerequisites which are needed
        so that the django SqlConnection model can be queried.
        """
        super().setUpClass()
        logger.debug("%s.setUpClass()", cls.test_smarter_plugin_broker_base_logger_prefix)
        test_sql_connection_loader = SAMLoader(file_path=MANIFEST_PATH_SQL_CONNECTION)
        apply_manifest(username=cls.admin_user.username, manifest=test_sql_connection_loader.yaml_data, verbose=True)

        # this should match spec.connection in ../data/sql-plugin.yaml
        # assumed to be: test_sql_connection
        cls.test_sql_connection_name = test_sql_connection_loader.manifest_metadata.get("name")
        if not cls.test_sql_connection_name:
            raise SmarterValueError("Failed to get test secret name from manifest metadata.")
        try:
            cls.sql_connection = SqlConnection.objects.get(
                account=cls.account,
                name=cls.test_sql_connection_name,
            )
        except SqlConnection.DoesNotExist as e:
            raise SmarterValueError(f"Failed to get test secret '{cls.test_sql_connection_name}' from database.") from e
        logger.debug(
            "%s.setUpClass() %s owned by %s created for connection broker tests.",
            cls.test_smarter_plugin_broker_base_logger_prefix,
            cls.test_sql_connection_name,
            cls.user_profile,
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up the created secret after all tests have run."""
        logger.debug("%s.tearDownClass()", cls.test_smarter_plugin_broker_base_logger_prefix)
        try:
            cls.sql_connection.delete()
            logger.debug(
                "%s.tearDownClass() Test SqlConnection %s owned by %s deleted after connection broker tests.",
                cls.test_smarter_plugin_broker_base_logger_prefix,
                cls.test_sql_connection_name,
                cls.user_profile,
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.tearDownClass() Failed to delete test SqlConnection %s owned by %s after connection broker tests: %s",
                cls.test_smarter_plugin_broker_base_logger_prefix,
                cls.test_sql_connection_name,
                cls.user_profile,
                str(e),
            )
        super().tearDownClass()
