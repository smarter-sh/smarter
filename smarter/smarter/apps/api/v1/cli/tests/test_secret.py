"""Test Api v1 CLI commands for secret"""

import json
import logging
import os
from datetime import datetime
from http import HTTPStatus
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from django.urls import reverse

from smarter.apps.account.manifest.brokers.secret import SAMSecret
from smarter.apps.account.models import Secret
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.api import SmarterApiVersions
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)
from smarter.lib.manifest.loader import SAMLoader

from .base_class import ApiV1CliTestBase


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level <= logging.INFO
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


KIND = SAMKinds.SECRET.value
HERE = os.path.abspath(os.path.dirname(__file__))


class TestApiCliV1Secret(ApiV1CliTestBase):
    """
    Test Api v1 CLI commands for secret

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, secret, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    def setUp(self):
        super().setUp()
        self.kwargs = {SAMKeys.KIND.value: KIND}

        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.query_params = urlencode({"name": self.name})

        self.secret_description = "TestApiCliV1Secret test description of the secret"
        self.secret_value = "testSecretValue_" + self.hash_suffix
        self.secret_expiration = datetime.now() + relativedelta(months=6)

    def tearDown(self):
        try:
            secret = Secret.objects.get(name=self.name, user_profile=self.user_profile)
            secret.delete()
        except Secret.DoesNotExist:
            pass

        return super().tearDown()

    def secret_factory(self) -> Secret:
        """
        Create a secret object for testing purposes.
        """
        secret = Secret.objects.create(
            user_profile=self.user_profile,
            name=self.name,
            description=self.secret_description,
            encrypted_value=Secret.encrypt(value=self.secret_value),
            expires_at=self.secret_expiration,
        )
        return secret

    def validate_response(self, response: dict) -> None:
        # validate the response and status are both good
        self.assertIsInstance(response, dict)

        # validate the structure of the response
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SECRET.value)

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
            "value",
            "expiration_date",
        ]
        for field in config_fields:
            assert field in config.keys(), f"{field} not found in config keys"

    def test_01_example_manifest(self) -> None:
        """Test example-manifest command"""
        path = reverse(self.namespace + ApiV1CliReverseViews.manifest, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        data = response[SCLIResponseGet.DATA.value]
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SECRET.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)

        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn("description", metadata.keys())

        # spec
        self.validate_spec(data)

    def test_02_apply(self):
        """
        Test that we get OK response when passing a valid manifest
        to apply()
        """
        # load the manifest from the yaml file
        loader = SAMLoader(file_path=os.path.join(HERE, "data", "good-secret.yaml"))
        self.assertTrue(loader.ready, msg="loader is not ready")

        # use the manifest to creata a new sqlconnection Pydantic model
        manifest = SAMSecret(**loader.pydantic_model_dump())

        # dump the manifest to json
        manifest_json = json.loads(manifest.model_dump_json())

        # retrieve the current manifest by calling "describe"
        path = reverse(self.namespace + ApiV1CliReverseViews.apply)
        response, status = self.get_response(path=path, data=manifest_json)

        logger.info("response=%s", response)
        expected_response = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Secret",
                "metadata": {
                    "name": "test_secret",
                    "description": "A secret for testing purposes",
                    "version": "0.1.0",
                    "tags": [],
                    "annotations": None,
                },
                "spec": {"config": {"value": "<-************->", "expiration_date": "2026-12-31"}},
                "status": {
                    "accountNumber": "6470-8514-9376",
                    "username": "testAdminUser_4dfe1bba21efb9d1",
                    "created": "2025-05-22T17:18:07.240344+00:00",
                    "updated": "2025-05-22T17:18:07.243639+00:00",
                    "last_accessed": None,
                },
            },
            "message": "Secret test_secret applied successfully",
            "api": "smarter.sh/v1",
            "thing": "Secret",
            "metadata": {"key": "f6866dee501b4272cd8d5128581bfc8d4e65b1fd9c229b8f36e8fe2df4d5d591"},
        }

        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Secret test_secret applied successfully")
        self.assertEqual(response["api"], SmarterApiVersions.V1)
        self.assertEqual(response["thing"], SAMKinds.SECRET.value)
        self.assertIsInstance(response["metadata"], dict)
        self.assertIn("key", response["metadata"])
        data: dict = response["data"]
        self.assertIsInstance(data, dict)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SECRET.value)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), "test_secret")
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("description", None), "A secret for testing purposes")
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("version", None), "0.1.0")
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("tags", None), [])
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("annotations"), [])

    def test_03_describe(self):
        """
        invoke the describe endpoint to verify that the Secret was created
        """
        secret = self.secret_factory()
        self.assertIsInstance(secret, Secret)

        path = f"{reverse(self.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        logger.info("response=%s", response)
        # pylint: disable=W0612
        expected_response = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Secret",
                "metadata": {
                    "name": "testd086c76a2de4aece",
                    "description": "TestApiCliV1Secret test description of the secret",
                    "version": "1.0.0",
                    "username": "testAdminUser_b388b2a865a89a14",
                    "accountNumber": "3079-5428-0765",
                    "tags": None,
                    "annotations": None,
                },
                "spec": {
                    "config": {
                        "value": "testSecretValue_d086c76a2de4aece",
                        "description": "TestApiCliV1Secret test description of the secret",
                        "expiration_date": None,
                    }
                },
                "status": {
                    "accountNumber": "3079-5428-0765",
                    "username": "testAdminUser_b388b2a865a89a14",
                    "created": "2025-05-22T17:46:12.518907+00:00",
                    "updated": "2025-05-22T17:46:12.518921+00:00",
                    "last_accessed": "2025-05-22T17:46:12.742687+00:00",
                },
            },
            "message": "Secret testd086c76a2de4aece described successfully",
            "api": "smarter.sh/v1",
            "thing": "Secret",
            "metadata": {"key": "7f93a8ce45b88595ec0cf2eb347e9c91939ca8815c9e927ff0c2769ecb5b8a79"},
        }

        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")
        self.assertIsInstance(response, dict)

        data: dict = response[SCLIResponseGet.DATA.value]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SECRET.value)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), self.name)

        # we should also be able to get the Secret by name
        path = f"{reverse(self.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=path)
        response = response["data"]
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.TITLES.value], list)
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.ITEMS.value], list)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SECRET.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), self.name)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("description", None), self.secret_description)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("version", None), "1.0.0")
        self.assertIn("tags", data.get(SAMKeys.METADATA.value, {}))
        self.assertIn("annotations", data.get(SAMKeys.METADATA.value, {}))
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("username", None), self.user_profile.user.username)
        self.assertEqual(
            data.get(SAMKeys.METADATA.value, {}).get("accountNumber", None), self.user_profile.account.account_number
        )

        spec: dict = data.get(SAMKeys.SPEC.value)
        config: dict = spec.get("config")
        self.assertIsInstance(config, dict)
        self.assertIn("value", config.keys())
        self.assertIn("description", config.keys())
        self.assertIn("expiration_date", config.keys())
        self.assertEqual(config["value"], self.secret_value)
        self.assertEqual(config["description"], self.secret_description)

        actual_exp: str = config["expiration_date"]
        actual_exp = actual_exp.replace("+00:00", "Z") if actual_exp else None
        expected_exp = self.secret_expiration.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.assertEqual(actual_exp, expected_exp)

        secret.delete()

    def test_04_delete(self) -> None:
        """Test delete command"""
        secret = self.secret_factory()
        self.assertIsInstance(secret, Secret)

        path = f"{reverse(self.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        logger.info("response=%s", response)

        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], f"Secret {self.name} deleted successfully")
        with self.assertRaises(Secret.DoesNotExist):
            Secret.objects.get(name=self.name, user_profile=self.user_profile)

    def test_05_deploy(self) -> None:
        """Test deploy command"""
        path = reverse(self.namespace + ApiV1CliReverseViews.deploy, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        logger.info("response=%s", response)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED.value)
        self.assertIsInstance(response, dict)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertIn("not implemented", error["description"])

    def test_06_undeploy(self) -> None:
        """Test undeploy command"""
        path = reverse(self.namespace + ApiV1CliReverseViews.undeploy, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED.value)
        self.assertIsInstance(response, dict)

        logger.info("response=%s", response)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertIn("not implemented", error["description"])

    def test_07_logs(self) -> None:
        """Test logs command"""
        path = reverse(self.namespace + ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED.value)
        self.assertIsInstance(response, dict)

        logger.info("response=%s", response)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertIn("not implemented", error["description"])
