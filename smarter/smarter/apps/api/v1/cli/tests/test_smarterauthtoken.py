"""Test Api v1 CLI commands for SmarterAuthToken"""

import logging
from http import HTTPStatus
from typing import Tuple
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.api import SmarterApiVersions
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.manifest.brokers.auth_token import SAMSmarterAuthToken
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader

from .base_class import ApiV1CliTestBase


KIND = SAMKinds.AUTH_TOKEN.value


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level >= logging.INFO
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestApiCliV1SmarterAuthToken(ApiV1CliTestBase):
    """
    Test Api v1 CLI commands for SmarterAuthToken

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and test_token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    test_token_record: SmarterAuthToken = None
    test_token: str = None

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
        """Create a SmarterAuthToken record for testing"""

        auth_token_record, secret_token = SmarterAuthToken.objects.create(
            name=self.name,
            user=self.admin_user,
            description=f"{self.__class__.__name__} Test API Key",
            is_active=True,
        )  # type: ignore
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
        path = reverse(self.namespace + ApiV1CliReverseViews.example_manifest, kwargs=kwargs)
        response, status = self.get_response(path=path)

        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        path = reverse(self.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

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
        self.assertTrue(loader.ready, msg="loader is not ready")

        # use the manifest to creata a new sqlconnection Pydantic model
        manifest = SAMSmarterAuthToken(**loader.pydantic_model_dump())

        # dump the manifest to json
        manifest_json = json.loads(manifest.model_dump_json())

        # retrieve the current manifest by calling "describe"
        path = reverse(self.namespace + ApiV1CliReverseViews.apply)
        response, status = self.get_response(path=path, data=manifest_json)

        # pylint: disable=W0612
        expected_output = {
            "data": {
                "key_id": "1f75ac53-5a9d-4746-aea5-355bbd6456cb",
                "name": "test_auth_token",
                "description": "An example Smarter API manifest for a AuthToken",
                "is_active": True,
                "last_used_at": None,
                "created_at": "2025-05-22T15:01:08.429107Z",
                "updated_at": "2025-05-22T15:01:08.431207Z",
            },
            "message": "Successfully created AuthToken test_auth_token with secret token <-- 64-CHARACTER SECRET TOKEN VALUE -->. Please store this token securely. It will not be shown again.",
            "api": "smarter.sh/v1",
            "thing": "AuthToken",
            "metadata": {"key": "93a6ec2afd7df6de526457b2234f117a454488e6af1d3fe577c46193b3dc61ef"},
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

        path = reverse(self.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # pylint: disable=W0612
        expected_output = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "AuthToken",
                "metadata": {"count": 2},
                "kwargs": {},
                "data": {
                    "titles": [
                        {"name": "keyId", "type": "UUIDField"},
                        {"name": "name", "type": "CharField"},
                        {"name": "description", "type": "CharField"},
                        {"name": "isActive", "type": "BooleanField"},
                        {"name": "lastUsedAt", "type": "DateTimeField"},
                        {"name": "createdAt", "type": "DateTimeField"},
                        {"name": "updatedAt", "type": "DateTimeField"},
                    ],
                    "items": [
                        {
                            "keyId": "e4824746-ef0d-4fcc-b2f7-44624448366f",
                            "name": "testAdminUser_446b2324315ee523",
                            "description": "testAdminUser_446b2324315ee523",
                            "isActive": True,
                            "lastUsedAt": "2025-05-22T14:50:38.036133Z",
                            "createdAt": "2025-05-22T14:50:37.812581Z",
                            "updatedAt": "2025-05-22T14:50:38.037580Z",
                        },
                        {
                            "keyId": "47f6e801-f291-4b02-af8b-9bb08c3baf43",
                            "name": "testd2ce00af3382939e",
                            "description": "TestApiCliV1SmarterAuthToken Test API Key",
                            "isActive": True,
                            "lastUsedAt": None,
                            "createdAt": "2025-05-22T14:50:37.815417Z",
                            "updatedAt": "2025-05-22T14:50:37.815450Z",
                        },
                    ],
                },
            },
            "message": "AuthTokens got successfully",
            "api": "smarter.sh/v1",
            "thing": "AuthToken",
            "metadata": {"key": "3b30e0fc485f6d89e587f93e28f15bef2fbd7e0f39f69fd5125dc213c1454e2b"},
        }

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
        """Test deploy command"""
        kwargs = {"kind": KIND}
        path = reverse(self.namespace + ApiV1CliReverseViews.deploy, kwargs=kwargs)
        query_params = urlencode({"name": self.test_token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # pylint: disable=W0612
        exected_output = {
            "data": {
                "key_id": "e9099b4d-fb44-492a-8e69-3545e0799a79",
                "name": "test15fc3f69c5db1505",
                "description": "TestApiCliV1SmarterAuthToken Test API Key",
                "is_active": True,
                "last_used_at": None,
                "created_at": "2025-05-22T15:04:46.143163Z",
                "updated_at": "2025-05-22T15:04:46.143173Z",
            },
            "message": "AuthToken test15fc3f69c5db1505 deployed successfully",
            "api": "smarter.sh/v1",
            "thing": "AuthToken",
            "metadata": {"key": "62124001b5f517173f5863df0ab44f109f8ae1a8e7f91b9b541d3370f236a95b"},
        }

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.test_token_record.refresh_from_db()
        self.assertTrue(self.test_token_record.is_active)
        self.assertTrue(response[SmarterJournalApiResponseKeys.DATA]["is_active"])

    def test_undeploy(self) -> None:
        """Test undeploy command"""
        kwargs = {"kind": KIND}
        path = reverse(self.namespace + ApiV1CliReverseViews.undeploy, kwargs=kwargs)
        query_params = urlencode({"name": self.test_token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # pylint: disable=W0612
        expected_output = {
            "data": {
                "key_id": "d04f1e2f-8985-43f4-90bf-8e08ca3af50d",
                "name": "testf4c182d5cc4310ad",
                "description": "TestApiCliV1SmarterAuthToken Test API Key",
                "is_active": False,
                "last_used_at": None,
                "created_at": "2025-05-22T15:06:17.801931Z",
                "updated_at": "2025-05-22T15:06:18.028426Z",
            },
            "message": "AuthToken testf4c182d5cc4310ad undeployed successfully",
            "api": "smarter.sh/v1",
            "thing": "AuthToken",
            "metadata": {"key": "0f62e44b44cc9691f79c7b4ae47e66a52c70dbff54662645c331c6f04736703d"},
        }

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.test_token_record.refresh_from_db()
        self.assertFalse(self.test_token_record.is_active)
        self.assertFalse(response[SmarterJournalApiResponseKeys.DATA]["is_active"])

    def test_delete(self) -> None:
        """Test delete command"""
        path = reverse(self.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # pylint: disable=W0612
        exected_output = {
            "message": "AuthToken test06bfeb5de52cd5d3 deleted successfully",
            "api": "smarter.sh/v1",
            "thing": "AuthToken",
            "metadata": {"key": "bb31badf5706e7484c199e99a2985a1494802861c5ce62130fb3a8aa1185b694"},
        }

        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn("deleted successfully", response["message"])
        self.assertEqual(response["thing"], "AuthToken")
        self.assertEqual(response["api"], "smarter.sh/v1")
        self.assertIn("metadata", response)
        self.assertIn("command", response["metadata"].keys())

        # verify the SmarterAuthToken was deleted
        try:
            SmarterAuthToken.objects.get(name=self.name, user=self.admin_user)
            self.fail("SqlConnection was not deleted")
        except SmarterAuthToken.DoesNotExist:
            pass

    def test_logs(self) -> None:
        """Test logs command"""
        path = reverse(self.namespace + ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # pylint: disable=W0612
        expected_output = {
            "error": {
                "errorClass": "str",
                "stacktrace": "Traceback (most recent call last):\n  File /home/smarter_user/smarter/smarter/apps/api/v1/cli/views/base.py, line 345, in dispatch\n    response = super().dispatch(request, *args, **kwargs)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File /home/smarter_user/venv/lib/python3.12/site-packages/rest_framework/views.py, line 509, in dispatch\n    response = self.handle_exception(exc)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File /home/smarter_user/venv/lib/python3.12/site-packages/rest_framework/views.py, line 469, in handle_exception\n    self.raise_uncaught_exception(exc)\n  File /home/smarter_user/venv/lib/python3.12/site-packages/rest_framework/views.py, line 480, in raise_uncaught_exception\n    raise exc\n  File /home/smarter_user/venv/lib/python3.12/site-packages/rest_framework/views.py, line 506, in dispatch\n    response = handler(request, *args, **kwargs)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File /home/smarter_user/smarter/smarter/apps/api/v1/cli/views/logs.py, line 45, in post\n    return self.broker.logs(request=request, kwargs=kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File /home/smarter_user/smarter/smarter/lib/drf/manifest/brokers/auth_token.py, line 396, in logs\n    raise SAMBrokerErrorNotImplemented(message=Logs are not implemented, thing=self.kind, command=command)\nsmarter.lib.manifest.broker.SAMBrokerErrorNotImplemented: Smarter API AuthToken manifest broker: logs() not implemented error.  Logs are not implemented: Logs are not implemented\n",
                "description": "Smarter API AuthToken manifest broker: logs() not implemented error.  Logs are not implemented",
                "status": "501",
                "args": "url=http://testserver/api/v1/cli/logs/AuthToken/?name=test7d07dcc4e2fd10c0",
                "cause": "Python Exception",
                "context": "thing=AuthToken, command=logs",
            },
            "api": "smarter.sh/v1",
            "thing": "AuthToken",
            "metadata": {"key": "76fa29bf20917097b4aedd0e23535dd7562e13a7af060563c8c6b2291e4ce7b4"},
        }

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertIsInstance(response, dict)
