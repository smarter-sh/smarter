"""Test Api v1 CLI commands for account"""

from http import HTTPStatus

import yaml
from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys


class TestApiCliV1Account(ApiV1TestBase):
    """
    Test Api v1 CLI commands for account

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    def validate_response(self, response: dict) -> None:
        # validate the response and status are both good
        self.assertIsInstance(response, dict)

        # validate the structure of the response
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1.value)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.ACCOUNT.value)

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
            "companyName",
            "phoneNumber",
            "address1",
            "address2",
            "city",
            "state",
            "postalCode",
            "country",
            "language",
            "timezone",
            "currency",
        ]
        for field in config_fields:
            assert field in config.keys(), f"{field} not found in config keys"

    def test_example_manifest(self) -> None:
        """Test example-manifest command"""

        kwargs = {"kind": "account"}
        path = reverse(ApiV1CliReverseViews.example_manifest, kwargs=kwargs)
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn("accountNumber", metadata.keys())

        # spec
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        kwargs = {"kind": "account"}
        path = reverse(ApiV1CliReverseViews.describe, kwargs=kwargs)
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_apply(self) -> None:
        """Test apply command"""

        kwargs = {"kind": "account"}
        path = reverse(ApiV1CliReverseViews.describe, kwargs=kwargs)
        response, status = self.get_response(path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        data = response[SmarterJournalApiResponseKeys.DATA]
        data[SAMKeys.SPEC.value] = {
            "companyName": "test data",
            "phoneNumber": "+1 617 834 6172",
            "address1": "Avenida Reforma 222",
            "address2": "Piso 19",
            "city": "CDMX",
            "state": "CDMX",
            "postalCode": "06600",
            "country": "Mexico",
            "language": "es-ES",
            "timezone": "America/Mexico_City",
            "currency": "MXN",
        }
        data.pop(SAMKeys.STATUS.value)  # status is read-only
        manifest = yaml.dump(data)
        print("manifest:\n", manifest)
        path = reverse(ApiV1CliReverseViews.apply)
        response, status = self.get_response(path, manifest=manifest)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        print("response:\n", response)

    def test_get(self) -> None:
        """Test get command"""
        pass

    def test_deploy(self) -> None:
        """Test deploy command"""
        pass

    def test_undeploy(self) -> None:
        """Test undeploy command"""
        pass

    def test_logs(self) -> None:
        """Test logs command"""
        pass

    def test_delete(self) -> None:
        """Test delete command"""
        pass
