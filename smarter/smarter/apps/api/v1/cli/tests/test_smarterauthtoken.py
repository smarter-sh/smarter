"""Test Api v1 CLI commands for SmarterAuthToken"""

import json
from http import HTTPStatus
from logging import getLogger
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.common.api import SmarterApiVersions
from smarter.lib.drf.manifest.brokers.auth_token import SAMSmarterAuthToken
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader


KIND = SAMKinds.AUTH_TOKEN.value
logger = getLogger(__name__)


class TestApiCliV1SmarterAuthToken(ApiV1TestBase):
    """
    Test Api v1 CLI commands for SmarterAuthToken

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and test_token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.query_params = urlencode({"name": self.name})
        self.user = self.admin_user
        self.test_token_record, self.test_token = self.auth_token_factory()

    def tearDown(self) -> None:
        """Tear down test fixtures."""

        try:
            if self.test_token_record:
                self.test_token_record.delete()
        # pylint: disable=W0718
        except Exception as e:
            logger.error("Error deleting test_token record: %s", e)

        super().tearDown()

    def auth_token_factory(self) -> SmarterAuthToken:
        """Create a SmarterAuthToken record for testing"""

        auth_token_record, secret_token = SmarterAuthToken.objects.create(
            name=self.name,
            user=self.admin_user,
            description=f"{self.__class__.__name__} Test API Key",
            is_active=True,
        )
        return auth_token_record, secret_token

    def validate_response(self, response: dict) -> None:
        # validate the response and status are both good
        self.assertIsInstance(response, dict)

        # validate the structure of the response
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.AUTH_TOKEN.value)

        # validate the metadata
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, data.keys())
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn(SAMMetadataKeys.NAME.value, metadata.keys())
        self.assertIn(SAMMetadataKeys.DESCRIPTION.value, metadata.keys())
        self.assertIn(SAMMetadataKeys.VERSION.value, metadata.keys())

    def validate_spec(self, data: dict) -> None:
        self.assertIn(SAMKeys.SPEC.value, data.keys())
        spec = data[SAMKeys.SPEC.value]
        config = spec["config"]
        config_fields = [
            "isActive",
            "username",
        ]
        for field in config_fields:
            assert field in config.keys(), f"{field} not found in config keys"

    def test_example_manifest(self) -> None:
        """Test example-manifest command"""

        # pylint: disable=W0612
        expected_output = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "AuthToken",
                "metadata": {
                    "name": "snake-case-name",
                    "description": "An example Smarter API manifest for a AuthToken",
                    "version": "1.0.0",
                },
                "spec": {"config": {"isActive": True, "username": "valid_smarter_username"}},
            },
            "message": "AuthToken example manifest successfully generated",
            "api": "smarter.sh/v1",
            "thing": "AuthToken",
            "metadata": {"key": "bda17c93b9436934525733f32ad20279ca8868411954d69041b913627e931ad1"},
        }

        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.example_manifest, kwargs=kwargs)
        response, status = self.get_response(path=path)

        logger.info("Response: %s", response)

        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        path = reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        logger.info("Response: %s", response)
        # pylint: disable=W0612
        expected_output = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "AuthToken",
                "metadata": {
                    "name": "test03b41ac45632817b",
                    "description": "TestApiCliV1SmarterAuthToken Test API Key",
                    "version": "1.0.0",
                },
                "spec": {"config": {"isActive": True, "username": "testAdminUser_67dc143ec3cae0c1"}},
                "status": {
                    "created": "2025-05-22T13:22:38.473613+00:00",
                    "modified": "2025-05-22T13:22:38.473628+00:00",
                    "lastUsedAt": None,
                },
            },
            "message": "AuthToken test03b41ac45632817b described successfully",
            "api": "smarter.sh/v1",
            "thing": "AuthToken",
            "metadata": {"key": "353caf5c9b603e3c093c1d5a9e80bb4774e74da4e64a0d1601350fcdb48c370f"},
        }

        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_apply(self) -> None:
        """Test apply command"""

        # load the manifest from the yaml file
        loader = SAMLoader(file_path="smarter/lib/drf/tests/data/auth-token.yaml")

        # use the manifest to creata a new sqlconnection Pydantic model
        manifest = SAMSmarterAuthToken(**loader.pydantic_model_dump())

        # dump the manifest to json
        manifest_json = json.loads(manifest.model_dump_json())

        # retrieve the current manifest by calling "describe"
        path = reverse(ApiV1CliReverseViews.apply)
        response, status = self.get_response(path=path, data=manifest_json)

        logger.info("Response: %s", response)
        expected_output = {
            "message": "Successfully created AuthToken test_auth_token with secret token <-- 64-CHARACTER SECRET TOKEN VALUE -->. Please store this token securely. It will not be shown again.",
            "api": "smarter.sh/v1",
            "thing": "AuthToken",
            "metadata": {"key": "5f8a81d3a12d12f6b780b096c4f6602c28bebd609962b634a92181943d034754"},
        }

        self.assertEqual(status, HTTPStatus.OK)

        try:
            test_auth_token = SmarterAuthToken.objects.get(name="test_auth_token", user=self.admin_user)
            test_auth_token.delete()
        except SmarterAuthToken.DoesNotExist:
            self.fail("Test auth test_token was not created")

    def test_get(self) -> None:
        """Test get command"""

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
                return False

            title_names = {title["name"] for title in data["titles"]}

            for item in data["items"]:
                if not isinstance(item, dict):
                    return False
                if set(item.keys()) != title_names:
                    return False

            return True

        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.get, kwargs=kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.AUTH_TOKEN.value)

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
        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.deploy, kwargs=kwargs)
        query_params = urlencode({"name": self.test_token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.test_token_record.refresh_from_db()
        self.assertTrue(self.test_token_record.is_active)

    def test_undeploy(self) -> None:
        """Test undeploy command"""
        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.undeploy, kwargs=kwargs)
        query_params = urlencode({"name": self.test_token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.test_token_record.refresh_from_db()
        self.assertFalse(self.test_token_record.is_active)

        # re-deploy the test_token so that it can be deleted
        self.test_token_record.is_active = True
        self.test_token_record.save()

    def test_logs(self) -> None:
        """Test logs command"""
        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.logs, kwargs=kwargs)
        query_params = urlencode({"name": self.test_token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
