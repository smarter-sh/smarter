"""Test Api v1 CLI commands for secret"""

import logging
import os
from datetime import datetime
from http import HTTPStatus
from typing import Optional, Union
from urllib.parse import urlencode

import pytz
from dateutil.relativedelta import relativedelta
from django.db.models.signals import post_delete
from django.urls import reverse

from smarter.apps.account.manifest.brokers.secret import SAMSecret
from smarter.apps.account.models import Secret
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.api import SmarterApiVersions
from smarter.lib import json
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
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.PLUGIN_LOGGING
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
        self.secret_expiration = datetime.now(tz=pytz.UTC) + relativedelta(months=6)

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
        logger.info("response=%s", response)
        self.assertEqual(status, HTTPStatus.OK)
        data = response[SCLIResponseGet.DATA.value]
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

        logger.info("manifest_json=%s", json.dumps(manifest_json))

        # retrieve the current manifest by calling "describe"
        path = reverse(self.namespace + ApiV1CliReverseViews.apply)
        response, status = self.get_response(path=path, data=manifest_json)
        self.assertIsInstance(response, dict)
        logger.info("response=%s", json.dumps(response, indent=4))
        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")

        # pylint: disable=W0612
        expected_response = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Secret",
                "metadata": {"count": 1},
                "kwargs": {},
                "data": {
                    "titles": [
                        {"name": "id", "type": "IntegerField"},
                        {"name": "createdAt", "type": "DateTimeField"},
                        {"name": "updatedAt", "type": "DateTimeField"},
                        {"name": "name", "type": "CharField"},
                        {"name": "description", "type": "CharField"},
                        {"name": "version", "type": "CharField"},
                        {"name": "annotations", "type": "JSONField"},
                        {"name": "lastAccessed", "type": "DateTimeField"},
                        {"name": "expiresAt", "type": "DateTimeField"},
                        {"name": "encryptedValue", "type": "ModelField"},
                        {"name": "account", "type": "PrimaryKeyRelatedField"},
                        {"name": "userProfile", "type": "PrimaryKeyRelatedField"},
                    ],
                    "items": [
                        {
                            "apiVersion": "smarter.sh/v1",
                            "kind": "Secret",
                            "metadata": {
                                "name": "smarter_test_base_e3ae3f4cd5be8d0f",
                                "description": "TestApiCliV1Secret test description of the secret",
                                "version": "1.0.0",
                                "tags": [],
                                "annotations": [],
                            },
                            "spec": {
                                "config": {
                                    "value": "testSecretValue_e3ae3f4cd5be8d0f",
                                    "expirationDate": "2026-07-07T15:39:37.425Z",
                                }
                            },
                            "status": {
                                "accountNumber": "2671-0577-9207",
                                "username": "test_admin_user_91cddd4c6761e0a2",
                                "created": "2026-01-07T15:39:37.426Z",
                                "modified": "2026-01-07T15:39:37.426Z",
                                "lastAccessed": "2026-01-07T15:39:37.949Z",
                            },
                        }
                    ],
                },
            },
            "message": "Secrets got successfully",
            "api": "smarter.sh/v1",
            "thing": "Secret",
            "metadata": {"key": "b37b76d5304a1a5aa19d0ce1400f5778633c5bf1c499e2049b3ee3546c606366"},
        }

        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Secret test_secret applied successfully")
        self.assertEqual(response["api"], SmarterApiVersions.V1)
        self.assertEqual(response["thing"], SAMKinds.SECRET.value)
        self.assertIsInstance(response["metadata"], dict)

        data: dict = response["data"]
        self.assertIsInstance(data, dict)
        self.assertIn("name", data["data"]["metadata"])
        self.assertIn("description", data["data"]["metadata"])
        self.assertIn("version", data["data"]["metadata"])

        data: dict = response["data"]["data"]
        self.assertIsInstance(data, dict)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SECRET.value)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), manifest.metadata.name)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("description", None), manifest.metadata.description)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("version", None), manifest.metadata.version)

        manifest_metadata_tags = set(manifest.metadata.tags or [])
        response_metadata_tags = set(data.get(SAMKeys.METADATA.value, {}).get("tags", []) or [])
        self.assertEqual(
            response_metadata_tags,
            manifest_metadata_tags,
            msg=f"manifest={manifest_metadata_tags} response={response_metadata_tags}",
        )

        def sort_annotations(annotations):
            return sorted(annotations, key=lambda d: sorted(d.items()))

        manifest_metadata_annotations = json.dumps(sort_annotations(manifest.metadata.annotations) or {})
        logger.debug("manifest_metadata_annotations=%s", manifest_metadata_annotations)

        response_metadata_annotations = json.dumps(
            sort_annotations(data.get(SAMKeys.METADATA.value, {}).get("annotations", {}) or {})
        )
        logger.debug("response_metadata_annotations=%s", response_metadata_annotations)

        self.assertEqual(
            manifest_metadata_annotations,
            response_metadata_annotations,
            msg=f"manifest={manifest_metadata_annotations} response={response_metadata_annotations}",
        )

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
        logger.debug("response=%s", json.dumps(response, indent=4))
        received = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Secret",
                "metadata": {"count": 1},
                "kwargs": {},
                "data": {
                    "titles": [
                        {"name": "id", "type": "IntegerField"},
                        {"name": "createdAt", "type": "DateTimeField"},
                        {"name": "updatedAt", "type": "DateTimeField"},
                        {"name": "name", "type": "CharField"},
                        {"name": "description", "type": "CharField"},
                        {"name": "version", "type": "CharField"},
                        {"name": "annotations", "type": "JSONField"},
                        {"name": "lastAccessed", "type": "DateTimeField"},
                        {"name": "expiresAt", "type": "DateTimeField"},
                        {"name": "encryptedValue", "type": "ModelField"},
                        {"name": "account", "type": "PrimaryKeyRelatedField"},
                        {"name": "userProfile", "type": "PrimaryKeyRelatedField"},
                    ],
                    "items": [
                        {
                            "apiVersion": "smarter.sh/v1",
                            "kind": "Secret",
                            "metadata": {
                                "name": "smarter_test_base_421d46e4225eb63b",
                                "description": "TestApiCliV1Secret test description of the secret",
                                "version": "1.0.0",
                                "tags": [],
                                "annotations": [],
                            },
                            "spec": {
                                "config": {
                                    "value": "testSecretValue_421d46e4225eb63b",
                                    "expirationDate": "2026-07-07T15:24:43.503Z",
                                }
                            },
                            "status": {
                                "accountNumber": "0602-6859-0637",
                                "username": "test_admin_user_08f44abde3443f54",
                                "created": "2026-01-07T15:24:43.504Z",
                                "modified": "2026-01-07T15:24:43.504Z",
                                "lastAccessed": "2026-01-07T15:24:43.880Z",
                            },
                        }
                    ],
                },
            },
            "message": "Secrets got successfully",
            "api": "smarter.sh/v1",
            "thing": "Secret",
            "metadata": {"key": "e8ea54df1efbedbdbe727f6abcc92ea2f8b0f4513928d58114b0a2b9265f7222"},
        }

        data: dict = response[SCLIResponseGet.DATA.value]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SECRET.value)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), self.name)

        # we should also be able to get the Secret by name
        path = f"{reverse(self.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=path)
        logger.info("response=%s", response)
        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")
        self.assertIsInstance(response, dict)
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

        spec: dict = data.get(SAMKeys.SPEC.value, {})
        config: dict = spec.get("config", {})
        self.assertIsInstance(config, dict)
        self.assertIn("value", config.keys())
        self.assertIn("expiration_date", config.keys())
        self.assertEqual(config["value"], self.secret_value)

        actual_exp: Optional[Union[datetime, str]] = config.get("expiration_date")
        if not actual_exp:
            self.fail("expiration_date is None")
        if isinstance(actual_exp, str):
            if actual_exp.endswith("Z"):
                actual_exp = actual_exp[:-1] + "+00:00"
            actual_exp = datetime.fromisoformat(actual_exp)
        expected_exp = self.secret_expiration
        actual_exp = actual_exp.replace(microsecond=(actual_exp.microsecond // 1000) * 1000)
        expected_exp = expected_exp.replace(microsecond=(expected_exp.microsecond // 1000) * 1000)
        self.assertEqual(actual_exp, expected_exp, msg=f"expected={expected_exp} actual={actual_exp}")

        secret.delete()

    def test_04_delete(self) -> None:
        """Test delete command"""
        called = {}

        def secret_post_delete(sender, instance, **kwargs):
            called["was_called"] = True

        post_delete.connect(secret_post_delete, sender=Secret)

        secret = self.secret_factory()
        self.assertIsInstance(secret, Secret)

        path = f"{reverse(self.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        logger.info("response=%s", response)

        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], f"Secret {self.name} deleted successfully")

        post_delete.disconnect(secret_post_delete, sender=Secret)
        if not called.get("was_called"):
            self.fail("post_delete signal receiver was not called")

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
