"""Test Api v1 CLI commands for SqlConnection"""

import logging
from http import HTTPStatus
from typing import Optional
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.account.models import Secret
from smarter.apps.account.tests.factories import secret_factory
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.manifest.models.sql_connection.enum import (
    DbEngines,
    DBMSAuthenticationMethods,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.models import SqlConnection
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import smarter_settings
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader

from .base_class import ApiV1CliTestBase


KIND = SAMKinds.SQL_CONNECTION.value


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.PLUGIN_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestApiCliV1SqlConnection(ApiV1CliTestBase):
    """
    Test Api v1 CLI commands for SqlConnection

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    sqlconnection: Optional[SqlConnection] = None  # Ensure attribute always exists

    def setUp(self):
        super().setUp()
        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.query_params = urlencode({"name": self.name})
        self.password: Optional[Secret] = None

    def tearDown(self):
        if self.sqlconnection is not None:
            try:
                if self.sqlconnection.id is not None:  # type: ignore
                    self.sqlconnection.delete()
            except (SqlConnection.DoesNotExist, ValueError):
                pass
        if self.password is not None:
            try:
                if self.password.id is not None:  # type: ignore
                    self.password.delete()
            except (Secret.DoesNotExist, ValueError):
                pass
        super().tearDown()

    def sqlconnection_factory(self):
        """
        Create a sqlconnection for testing purposes.
        """
        self.password = secret_factory(
            user_profile=self.user_profile,
            name=self.name,
            description="smarter local dev password",
            value="smarter",
        )
        sqlconnection = SqlConnection.objects.create(
            account=self.account,
            name=self.name,
            kind=KIND,
            description="local mysql test sqlconnection - ",
            db_engine=DbEngines.MYSQL.value,
            authentication_method=DBMSAuthenticationMethods.TCPIP.value,
            timeout=300,
            hostname="smarter-mysql",
            port=3306,
            database="smarter",
            username="smarter",
            password=self.password,
        )
        return sqlconnection

    def validate_response(self, response: dict) -> None:
        # validate the response and status are both good
        self.assertIsInstance(response, dict)

        # validate the structure of the response
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SQL_CONNECTION.value)

        # validate the metadata
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, data.keys())
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn(SAMMetadataKeys.NAME.value, metadata.keys())
        self.assertIn(SAMMetadataKeys.DESCRIPTION.value, metadata.keys())
        self.assertIn(SAMMetadataKeys.VERSION.value, metadata.keys())

    def validate_spec(self, data: dict) -> None:
        self.assertIn(SAMKeys.SPEC.value, data.keys())
        spec = data[SAMKeys.SPEC.value]
        connection = spec["connection"]
        config_fields = ["dbEngine", "hostname", "port", "username", "password", "database"]
        for field in config_fields:
            assert field in connection.keys(), f"{field} not found in config keys: {connection.keys()}"

    def test_example_manifest(self) -> None:
        """Test example-manifest command"""

        path = reverse(self.namespace + ApiV1CliReverseViews.example_manifest, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        self.sqlconnection = self.sqlconnection_factory()

        path = reverse(self.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

        # verify the data matches the sqlconnection
        self.assertEqual(data[SAMKeys.METADATA.value][SAMMetadataKeys.NAME.value], self.sqlconnection.name)
        self.assertEqual(
            data[SAMKeys.METADATA.value][SAMMetadataKeys.DESCRIPTION.value], self.sqlconnection.description
        )
        self.assertEqual(data[SAMKeys.METADATA.value][SAMMetadataKeys.VERSION.value], self.sqlconnection.version)

        self.sqlconnection.delete()

    def test_apply(self) -> None:
        """Test apply command"""

        password_secret = secret_factory(
            user_profile=self.user_profile,
            name="smarter",
            description="test_apply() smarter local dev password",
            value="smarter",
        )

        # load the manifest from the yaml file
        loader = SAMLoader(file_path="smarter/apps/plugin/tests/mock_data/sql-connection.yaml")
        self.assertTrue(loader.ready, msg="loader is not ready")

        # use the manifest to creata a new sqlconnection Pydantic model
        manifest = SAMSqlConnection(**loader.pydantic_model_dump())

        # dump the manifest to json
        manifest_json = json.loads(manifest.model_dump_json())

        # retrieve the current manifest by calling "describe"
        path = reverse(self.namespace + ApiV1CliReverseViews.apply)
        response, status = self.get_response(path=path, data=manifest_json)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        logger.info("response: %s", response)

        # tear down the test results.
        sql_connection = SqlConnection.objects.get(name=manifest.metadata.name, account=self.account)
        sql_connection.delete()
        password_secret.delete()

    def test_get(self) -> None:
        """Test get command"""

        self.sqlconnection = self.sqlconnection_factory()
        path = reverse(self.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        logger.info("get() raw response: %s", response)

        expected_output = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "SqlConnection",
                "name": "smarter_test_base_7e1abbdf13b16e06",
                "metadata": {"count": 1},
                "kwargs": {"kwargs": {}},
                "data": {
                    "titles": [
                        {"name": "name", "type": "CharField"},
                        {"name": "description", "type": "CharField"},
                        {"name": "hostname", "type": "CharField"},
                        {"name": "port", "type": "IntegerField"},
                        {"name": "database", "type": "CharField"},
                        {"name": "username", "type": "CharField"},
                        {"name": "password", "type": "PrimaryKeyRelatedField"},
                        {"name": "proxyProtocol", "type": "ChoiceField"},
                        {"name": "proxyHost", "type": "CharField"},
                        {"name": "proxyPort", "type": "IntegerField"},
                        {"name": "proxyUsername", "type": "CharField"},
                        {"name": "proxyPassword", "type": "PrimaryKeyRelatedField"},
                    ],
                    "items": [
                        {
                            "name": "smarter_test_base_7e1abbdf13b16e06",
                            "description": "local mysql test sqlconnection - ",
                            "hostname": "smarter-mysql",
                            "port": 3306,
                            "database": "smarter",
                            "username": "smarter",
                            "password": 1156,
                            "proxyProtocol": "http",
                            "proxyHost": None,
                            "proxyPort": None,
                            "proxyUsername": None,
                            "proxyPassword": None,
                        }
                    ],
                },
            },
            "message": "SqlConnections got successfully",
            "api": "smarter.sh/v1",
            "thing": "SqlConnection",
            "metadata": {"key": "4ccb6c8cef5f9a98bf182b37c3240e3be29401ad1679a25135ce7e5cb0d404ca"},
        }

        self.assertEqual(status, HTTPStatus.OK)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # validate top-level keys
        self.assertIn("message", response)
        self.assertEqual(response["message"], "SqlConnections got successfully")
        self.assertIn("thing", response)
        self.assertEqual(response["thing"], "SqlConnection")
        self.assertIn("metadata", response.keys())
        self.assertIn(
            "count", response[SmarterJournalApiResponseKeys.DATA][SmarterJournalApiResponseKeys.METADATA].keys()
        )

        # validate titles
        expected_titles = [
            {"name": "name", "type": "CharField"},
            {"name": "description", "type": "CharField"},
            {"name": "hostname", "type": "CharField"},
            {"name": "port", "type": "IntegerField"},
            {"name": "database", "type": "CharField"},
            {"name": "username", "type": "CharField"},
            {"name": "password", "type": "PrimaryKeyRelatedField"},
            {"name": "proxyProtocol", "type": "ChoiceField"},
            {"name": "proxyHost", "type": "CharField"},
            {"name": "proxyPort", "type": "IntegerField"},
            {"name": "proxyUsername", "type": "CharField"},
            {"name": "proxyPassword", "type": "PrimaryKeyRelatedField"},
        ]

        # other structural checks
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())

        data = response["data"][SmarterJournalApiResponseKeys.DATA]
        logger.info("data: %s", data)
        expected_output = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "SqlConnection",
                "name": "smarter_test_base_21b4ec52db9ba67b",
                "metadata": {"count": 1},
                "kwargs": {"kwargs": {}},
                "data": {
                    "titles": [
                        {"name": "name", "type": "CharField"},
                        {"name": "description", "type": "CharField"},
                        {"name": "hostname", "type": "CharField"},
                        {"name": "port", "type": "IntegerField"},
                        {"name": "database", "type": "CharField"},
                        {"name": "username", "type": "CharField"},
                        {"name": "password", "type": "PrimaryKeyRelatedField"},
                        {"name": "proxyProtocol", "type": "ChoiceField"},
                        {"name": "proxyHost", "type": "CharField"},
                        {"name": "proxyPort", "type": "IntegerField"},
                        {"name": "proxyUsername", "type": "CharField"},
                        {"name": "proxyPassword", "type": "PrimaryKeyRelatedField"},
                    ],
                    "items": [
                        {
                            "name": "smarter_test_base_21b4ec52db9ba67b",
                            "description": "local mysql test sqlconnection - ",
                            "hostname": "smarter-mysql",
                            "port": 3306,
                            "database": "smarter",
                            "username": "smarter",
                            "password": 1155,
                            "proxyProtocol": "http",
                            "proxyHost": None,
                            "proxyPort": None,
                            "proxyUsername": None,
                            "proxyPassword": None,
                        }
                    ],
                },
            },
            "message": "SqlConnections got successfully",
            "api": "smarter.sh/v1",
            "thing": "SqlConnection",
            "metadata": {"key": "0515caf3d20e92bab3ef1b4f226b37a9bec26c0aada1e1e116781abd37d6cd4b"},
        }

        self.assertIn("data", response)
        self.assertIn("message", response)
        self.assertEqual(response["message"], "SqlConnections got successfully")
        self.assertIn("thing", response)
        self.assertEqual(response["thing"], "SqlConnection")
        self.assertIn("metadata", response)

        data = response["data"]
        self.assertIn("apiVersion", data)
        self.assertEqual(data["apiVersion"], "smarter.sh/v1")
        self.assertIn("kind", data)
        self.assertEqual(data["kind"], "SqlConnection")
        self.assertIn("metadata", data)
        self.assertIn("count", data["metadata"])
        self.assertIsInstance(data["metadata"]["count"], int)
        self.assertIn("kwargs", data)
        self.assertIn("data", data)

        data_data = data["data"]
        self.assertIn("titles", data_data)
        self.assertIsInstance(data_data["titles"], list)
        self.assertIn("items", data_data)
        self.assertIsInstance(data_data["items"], list)

        # Optionally, check the titles structure
        expected_titles = [
            {"name": "name", "type": "CharField"},
            {"name": "description", "type": "CharField"},
            {"name": "hostname", "type": "CharField"},
            {"name": "port", "type": "IntegerField"},
            {"name": "database", "type": "CharField"},
            {"name": "username", "type": "CharField"},
            {"name": "password", "type": "PrimaryKeyRelatedField"},
            {"name": "proxyProtocol", "type": "ChoiceField"},
            {"name": "proxyHost", "type": "CharField"},
            {"name": "proxyPort", "type": "IntegerField"},
            {"name": "proxyUsername", "type": "CharField"},
            {"name": "proxyPassword", "type": "PrimaryKeyRelatedField"},
        ]
        self.assertEqual(data_data["titles"], expected_titles)

    def test_deploy(self) -> None:
        """Test deploy command"""
        # create a sqlconnection so that we have something to deploy
        self.sqlconnection = self.sqlconnection_factory()

        path = reverse(self.namespace + ApiV1CliReverseViews.deploy, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        logger.info("response: %s", response)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)

    def test_undeploy(self) -> None:
        """Test undeploy command"""

        # create a sqlconnection so that we have something to undeploy
        self.sqlconnection = self.sqlconnection_factory()

        path = reverse(self.namespace + ApiV1CliReverseViews.undeploy, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        logger.info("response: %s", response)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)

    def test_logs(self) -> None:
        """Test logs command"""
        path = reverse(self.namespace + ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        logger.info("response: %s", response)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)

    def test_delete(self) -> None:
        """Test delete command"""
        # create a sqlconnection so that we have something to delete
        self.sqlconnection = self.sqlconnection_factory()

        path = reverse(self.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        logger.info("response: %s", response)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)

        # verify the sqlconnection was deleted
        try:
            SqlConnection.objects.get(name=self.name)
            self.fail("SqlConnection was not deleted")
        except SqlConnection.DoesNotExist:
            pass
