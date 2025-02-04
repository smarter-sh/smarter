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


KIND = SAMKinds.ACCOUNT.value


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

    def setUp(self):
        super().setUp()
        self.kwargs = {SAMKeys.KIND.value: KIND}

    def validate_response(self, response: dict) -> None:
        # validate the response and status are both good
        self.assertIsInstance(response, dict)

        # validate the structure of the response
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
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

        path = reverse(ApiV1CliReverseViews.example_manifest, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn("accountNumber", metadata.keys())

        # spec
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        path = reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_apply(self) -> None:
        """Test apply command"""

        # retrieve the current manifest by calling 'describe'
        path = reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # muck up the manifest with some test data
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

        # pop the status bc its read-only
        data.pop(SAMKeys.STATUS.value)

        # convert the data back to yaml, since this is what the cli usually sends
        manifest = yaml.dump(data)
        path = reverse(ApiV1CliReverseViews.apply)
        response, status = self.get_response(path=path, manifest=manifest)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # requery and validate our changes
        path = reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # validate our changes
        data = response[SmarterJournalApiResponseKeys.DATA]
        config = data[SAMKeys.SPEC.value]["config"]
        self.assertEqual(config["companyName"], self.account.company_name)
        self.assertEqual(config["phoneNumber"], self.account.phone_number)
        self.assertEqual(config["address1"], self.account.address1)
        self.assertEqual(config["address2"], self.account.address2)
        self.assertEqual(config["city"], self.account.city)
        self.assertEqual(config["state"], self.account.state)
        self.assertEqual(config["postalCode"], self.account.postal_code)
        self.assertEqual(config["country"], self.account.country)
        self.assertEqual(config["language"], self.account.language)
        self.assertEqual(config["timezone"], self.account.timezone)
        self.assertEqual(config["currency"], self.account.currency)

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

        path = reverse(ApiV1CliReverseViews.get, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.ACCOUNT.value)

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
        path = reverse(ApiV1CliReverseViews.deploy, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertIsInstance(response, dict)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertEqual(
            error["description"],
            "Smarter API Account manifest broker: deploy() not implemented error.  Deploy not implemented",
        )

    def test_undeploy(self) -> None:
        """Test undeploy command"""
        path = reverse(ApiV1CliReverseViews.undeploy, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertIsInstance(response, dict)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertEqual(
            error["description"],
            "Smarter API Account manifest broker: undeploy() not implemented error.  Undeploy not implemented",
        )

    def test_logs(self) -> None:
        """Test logs command"""
        path = reverse(ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

    def test_delete(self) -> None:
        """Test delete command"""
        path = reverse(ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertIsInstance(response, dict)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertEqual(
            error["description"],
            "Smarter API Account manifest broker: delete() not implemented error.  Delete not implemented",
        )
