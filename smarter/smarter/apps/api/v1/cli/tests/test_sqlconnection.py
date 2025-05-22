"""Test Api v1 CLI commands for SqlConnection"""

import json
from http import HTTPStatus
from logging import getLogger
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.account.models import Secret
from smarter.apps.account.tests.factories import secret_factory
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.plugin.manifest.models.sql_connection.enum import (
    DbEngines,
    DBMSAuthenticationMethods,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.models import SqlConnection
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader


KIND = SAMKinds.SQL_CONNECTION.value
logger = getLogger(__name__)


class TestApiCliV1SqlConnection(ApiV1TestBase):
    """
    Test Api v1 CLI commands for SqlConnection

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    sqlconnection: SqlConnection = None

    def setUp(self):
        super().setUp()
        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.query_params = urlencode({"name": self.name})
        self.password: Secret = None

    def tearDown(self):
        if self.sqlconnection is not None:
            try:
                self.sqlconnection.delete()
            except SqlConnection.DoesNotExist:
                pass
        if self.password is not None:
            try:
                self.password.delete()
            except Secret.DoesNotExist:
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
            name=self.name,
            db_engine=DbEngines.MYSQL.value,
            authentication_method=DBMSAuthenticationMethods.TCPIP.value,
            timeout=300,
            account=self.account,
            description="local mysql test sqlconnection - ",
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

        path = reverse(ApiV1CliReverseViews.example_manifest, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        self.sqlconnection = self.sqlconnection_factory()

        path = reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)
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

        # use the manifest to creata a new sqlconnection Pydantic model
        manifest = SAMSqlConnection(**loader.pydantic_model_dump())

        # dump the manifest to json
        manifest_json = json.loads(manifest.model_dump_json())

        # retrieve the current manifest by calling 'describe'
        path = reverse(ApiV1CliReverseViews.apply)
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

        # create a sqlconnection so that we have something to get.
        self.sqlconnection = self.sqlconnection_factory()

        def validate_titles(data):
            if "titles" not in data:
                return False

            for item in data["titles"]:
                if not isinstance(item, dict):
                    return False
                if "name" not in item or "type" not in item:
                    return False

            return True

        def validate_items(data):
            if "items" not in data or "titles" not in data:
                raise ValueError("items not found in data")

            if "titles" not in data:
                raise ValueError("titles not found in data")

            title_names = {title["name"] for title in data["titles"]}

            for item in data["items"]:
                if not isinstance(item, dict):
                    raise ValueError(f"item is not a dict: {item}")
                if set(item.keys()) != title_names:
                    difference = list(set(item.keys()).symmetric_difference(title_names))
                    raise ValueError(f"item keys do not match titles: {difference}")

            return True

        path = reverse(ApiV1CliReverseViews.get, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SQL_CONNECTION.value)

        # validate the metadata
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, data.keys())
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn("count", metadata.keys())
        self.assertEqual(metadata["count"], 1)

        # validate the response data dict, that it has both titles and items
        self.assertIn("data", data.keys())
        data = data["data"]
        self.assertIn("titles", data.keys())
        self.assertIn("items", data.keys())

        if not validate_titles(data):
            self.fail(f"Titles are not valid: {data}")

        if not validate_items(data):
            self.fail(f"Items are not valid: {data}")

    def test_deploy(self) -> None:
        """Test deploy command"""
        # create a sqlconnection so that we have something to deploy
        self.sqlconnection = self.sqlconnection_factory()

        path = reverse(ApiV1CliReverseViews.deploy, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)

    def test_undeploy(self) -> None:
        """Test undeploy command"""

        # create a sqlconnection so that we have something to undeploy
        self.sqlconnection = self.sqlconnection_factory()

        path = reverse(ApiV1CliReverseViews.undeploy, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)

    def test_logs(self) -> None:
        """Test logs command"""
        path = reverse(ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)

    def test_delete(self) -> None:
        """Test delete command"""
        # create a sqlconnection so that we have something to delete
        self.sqlconnection = self.sqlconnection_factory()

        path = reverse(ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)

        # verify the sqlconnection was deleted
        try:
            SqlConnection.objects.get(name=self.name)
            self.fail("SqlConnection was not deleted")
        except SqlConnection.DoesNotExist:
            pass
