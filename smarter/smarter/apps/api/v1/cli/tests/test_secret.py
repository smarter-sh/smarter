"""Test Api v1 CLI commands for secret"""

import os
import random
import string
from http import HTTPStatus
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.account.models import Secret
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.common.api import SmarterApiVersions
from smarter.common.const import PYTHON_ROOT
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)


KIND = SAMKinds.SECRET.value
HERE = os.path.abspath(os.path.dirname(__file__))


class TestApiCliV1Secret(ApiV1TestBase):
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
        hashstring = "".join(random.choices(string.ascii_letters + string.digits, k=8)).upper()
        self.kwargs = {SAMKeys.KIND.value: KIND}

        self.path = os.path.join(PYTHON_ROOT, "smarter/apps/api/v1/cli/tests/data")
        self.good_manifest_path = os.path.join(self.path, "good-secret.yaml")
        self.good_manifest_text = self.get_readonly_yaml_file(self.good_manifest_path)
        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.query_params = urlencode({"name": self.name})

        self.secret_description = "test description of the secret"
        self.secret_value = "testSecretValue_" + hashstring
        self.secret_expiration = "2026-01-01"

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
        path = reverse(ApiV1CliReverseViews.manifest, kwargs=self.kwargs)
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

        # create a Secret from a valid manifest
        path = reverse(ApiV1CliReverseViews.apply, kwargs=None)
        response, status = self.get_response(path, manifest=self.good_manifest_text)

        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], f"Secret {self.name} applied successfully")

    def test_03_describe(self):
        """
        invoke the describe endpoint to verify that the Secret was created
        """
        path = f"{reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")
        self.assertIsInstance(response, dict)

        data: dict = response[SCLIResponseGet.DATA.value]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SECRET.value)
        self.assertIsInstance(data.get(SAMKeys.METADATA.value, None), dict)
        self.assertEqual(data.get(SAMKeys.METADATA.value, {}).get("name", None), self.name)

        # we should also be able to get the Secret by name
        path = f"{reverse(ApiV1CliReverseViews.get, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=path)
        response = response["data"]
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.TITLES.value], list)
        self.assertIsInstance(response[SCLIResponseGet.DATA.value][SCLIResponseGetData.ITEMS.value], list)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.SECRET.value)
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)

    def test_04_delete(self) -> None:
        """Test delete command"""
        path = f"{reverse(ApiV1CliReverseViews.delete, kwargs=self.kwargs)}"
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK, msg=f"path={path} response={response}")
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], f"Secret {self.name} deleted successfully")
        with self.assertRaises(Secret.DoesNotExist):
            Secret.objects.get(name=self.name, user_profile=self.user_profile)

    def test_05_deploy(self) -> None:
        """Test deploy command"""
        path = reverse(ApiV1CliReverseViews.deploy, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED.value)
        self.assertIsInstance(response, dict)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertIn("Smarter API Secret manifest broker: deploy() not implemented", error["description"])

    def test_06_undeploy(self) -> None:
        """Test undeploy command"""
        path = reverse(ApiV1CliReverseViews.undeploy, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED.value)
        self.assertIsInstance(response, dict)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertIn("Smarter API Secret manifest broker: undeploy() not implemented", error["description"])

    def test_07_logs(self) -> None:
        """Test logs command"""
        path = reverse(ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK.value)
        self.assertIsInstance(response, dict)
