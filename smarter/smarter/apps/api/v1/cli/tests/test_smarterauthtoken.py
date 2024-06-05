"""Test Api v1 CLI commands for SmarterAuthToken"""

from http import HTTPStatus
from urllib.parse import urlencode

import yaml
from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys


KIND = SAMKinds.APIKEY.value


class TestApiCliV1SmarterAuthToken(ApiV1TestBase):
    """
    Test Api v1 CLI commands for SmarterAuthToken

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
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.APIKEY.value)

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

        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.example_manifest, kwargs=kwargs)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.describe, kwargs=kwargs)
        query_params = urlencode({"name": self.token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)

        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_apply(self) -> None:
        """Test apply command"""

        # retrieve the current manifest by calling 'describe'
        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.describe, kwargs=kwargs)
        query_params = urlencode({"name": self.token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # muck up the manifest with some test data
        data = response[SmarterJournalApiResponseKeys.DATA]
        data[SAMKeys.SPEC.value] = {
            "config": {
                "username": self.user.username,
                "isActive": True,
            }
        }
        data[SAMKeys.METADATA.value]["description"] = "new description"

        # pop the status bc its read-only
        data.pop(SAMKeys.STATUS.value)

        # convert the data back to yaml, since this is what the cli usually sends
        manifest = yaml.dump(data)
        path = reverse(ApiV1CliReverseViews.apply)
        response, status = self.get_response(path=path, manifest=manifest)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # requery and validate our changes
        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.describe, kwargs=kwargs)
        query_params = urlencode({"name": self.token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # validate our changes
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.METADATA.value]["description"], "new description")

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
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1.value)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.APIKEY.value)

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
        query_params = urlencode({"name": self.token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.token_record.refresh_from_db()
        self.assertTrue(self.token_record.is_active)

    def test_undeploy(self) -> None:
        """Test undeploy command"""
        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.undeploy, kwargs=kwargs)
        query_params = urlencode({"name": self.token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        _, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.token_record.refresh_from_db()
        self.assertFalse(self.token_record.is_active)

        # re-deploy the token so that it can be deleted
        self.token_record.is_active = True
        self.token_record.save()

    def test_logs(self) -> None:
        """Test logs command"""
        kwargs = {"kind": KIND}
        path = reverse(ApiV1CliReverseViews.logs, kwargs=kwargs)
        query_params = urlencode({"name": self.token_record.name})
        url_with_query_params = f"{path}?{query_params}"
        response, status = self.get_response(path=url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)
