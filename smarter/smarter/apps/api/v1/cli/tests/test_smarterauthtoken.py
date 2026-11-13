"""Test Api v1 CLI commands for SmarterAuthToken."""

from http import HTTPStatus
from typing import Tuple
from urllib.parse import urlencode

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.api import SmarterApiVersions
from smarter.lib import json, logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.manifest.brokers.auth_token import SAMSmarterAuthToken
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.typing import SmarterDictType

from .base_class import ApiV1CliTestBase

KIND = SAMKinds.AUTH_TOKEN.value


logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.API_LOGGING, SmarterWaffleSwitches.PLUGIN_LOGGING]
)


class TestApiCliV1SmarterAuthToken(ApiV1CliTestBase):
    """
    Test Api v1 CLI commands for SmarterAuthToken.

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and test_token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    test_token_record: SmarterAuthToken
    test_token: str

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

    def auth_token_factory(self) -> Tuple[SmarterAuthToken, str]:
        """Create a SmarterAuthToken record for testing."""

        auth_token_record, secret_token = SmarterAuthToken.objects.create(
            user_profile=self.user_profile,
            name=self.name,
            user=self.admin_user,
            description=f"{self.__class__.__name__} Test API Key",
            is_active=True,
        )  # type: ignore
        return auth_token_record, secret_token

    def validate_response(self, response: SmarterDictType) -> None:
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

    def validate_spec(self, data: SmarterDictType) -> None:
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
        """Test example-manifest command."""

        kwargs = {"kind": KIND}
        path = reverse(self.namespace + ApiV1CliReverseViews.example_manifest, kwargs=kwargs)
        response, status = self.get_response(path=path)

        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command."""
        path = reverse(self.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_apply(self) -> None:
        """Test apply command."""

        # load the manifest from the yaml file
        loader = SAMLoader(file_path="smarter/lib/drf/tests/data/auth-token.yaml")
        self.assertTrue(loader.ready, msg="loader is not ready")

        # use the manifest to creata a new sqlconnection Pydantic model
        manifest = SAMSmarterAuthToken(**loader.pydantic_model_dump())

        # dump the manifest to json
        manifest_json = json.loads(manifest.model_dump_json())

        # retrieve the current manifest by calling "describe"
        path = reverse(self.namespace + ApiV1CliReverseViews.apply)
        response, status = self.get_response(path=path, data=manifest_json)

        self.assertEqual(status, HTTPStatus.OK)

        try:
            test_auth_token = SmarterAuthToken.objects.get(
                name="test_auth_token", user__username=manifest.spec.config.username
            )
            test_auth_token.delete()
        except SmarterAuthToken.DoesNotExist:
            self.fail("Test auth test_token was not created")

    def test_get(self) -> None:
        """Test get command."""

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

        path = reverse(self.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)
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
        self.assertEqual(metadata["count"], 2)

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
        """Test deploy command."""
        kwargs = {"kind": KIND}
        path = reverse(self.namespace + ApiV1CliReverseViews.deploy, kwargs=kwargs)
        query_params = urlencode({"name": self.test_token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.test_token_record.refresh_from_db()
        self.assertTrue(self.test_token_record.is_active)
        self.assertEqual(response[SmarterJournalApiResponseKeys.DATA]["name"], self.test_token_record.name)

    def test_undeploy(self) -> None:
        """Test undeploy command."""
        kwargs = {"kind": KIND}
        path = reverse(self.namespace + ApiV1CliReverseViews.undeploy, kwargs=kwargs)
        query_params = urlencode({"name": self.test_token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.test_token_record.refresh_from_db()
        self.assertFalse(self.test_token_record.is_active)
        self.assertEqual(response[SmarterJournalApiResponseKeys.DATA]["name"], self.test_token_record.name)

    def test_delete(self) -> None:
        """Test delete command."""
        path = reverse(self.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn("deleted successfully", response["message"])
        self.assertEqual(response["metadata"]["thing"], "SmarterAuthToken")
        self.assertEqual(response["api"], "smarter.sh/v1")
        self.assertIn("metadata", response)

        # verify the SmarterAuthToken was deleted
        try:
            SmarterAuthToken.objects.get(name=self.name, user=self.admin_user)
            self.fail("SqlConnection was not deleted")
        except SmarterAuthToken.DoesNotExist:
            pass

    def test_logs(self) -> None:
        """Test logs command."""
        path = reverse(self.namespace + ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertIsInstance(response, dict)
