"""Test Api v1 CLI commands for account"""

import logging
from http import HTTPStatus

import yaml
from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from .base_class import ApiV1CliTestBase


KIND = SAMKinds.ACCOUNT.value


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestApiCliV1Account(ApiV1CliTestBase):
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

        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.example_manifest, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK.value)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn("accountNumber", metadata.keys())

        # spec
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.OK.value)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_apply(self) -> None:
        """
        Test apply command as follows:
        - call describe() and store the result
        - edit the result and call apply() and verify the results against our control set
        - call describe to verify that the changes were persisted.
        """

        logger.info("1.) get the manifest schema from the existing Account that we created in setup()")
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        logger.info(f"base response: {response}, Status: {status}")
        expected = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Account",
                "metadata": {
                    "name": "6031-2057-0556",
                    "description": "TestAccount_AdminUser_b0ead1318ceae5be",
                    "version": "1.0.0",
                },
                "spec": {
                    "config": {
                        "accountNumber": "6031-2057-0556",
                        "isDefaultAccount": False,
                        "companyName": "TestAccount_AdminUser_b0ead1318ceae5be",
                        "phoneNumber": "123-456-789",
                        "address1": None,
                        "address2": None,
                        "city": None,
                        "state": None,
                        "postalCode": None,
                        "country": "USA",
                        "language": "EN",
                        "timezone": None,
                        "currency": "USD",
                        "isActive": True,
                    }
                },
                "status": {
                    "created": "2025-08-23T16:22:03.853792+00:00",
                    "modified": "2025-08-23T16:22:03.853816+00:00",
                },
            },
            "message": "Account None described successfully",
            "api": "smarter.sh/v1",
            "thing": "Account",
            "metadata": {"command": "describe"},
        }

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK.value)
        self.assertIsInstance(response, dict)

        # modify the existing address information for the account
        data = response[SmarterJournalApiResponseKeys.DATA]
        change_set = data[SAMKeys.SPEC.value]["config"]
        change_set["address1"] = "Avenida Reforma 222"
        change_set["address2"] = "Piso 19"
        change_set["city"] = "CDMX"
        change_set["companyName"] = "test data"
        change_set["country"] = "Mexico"
        change_set["currency"] = "MXN"
        change_set["language"] = "es-ES"
        change_set["phoneNumber"] = "+1 617 834 6172"
        change_set["postalCode"] = "06600"
        change_set["state"] = "CDMX"
        change_set["timezone"] = "America/Mexico_City"
        data[SAMKeys.SPEC.value] = change_set

        # pop the status bc its read-only
        data.pop(SAMKeys.STATUS.value)

        # convert the data back to yaml, since this is what the cli usually receives
        manifest = yaml.dump(data)
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.apply)

        logger.info("2.) apply the modified manifest to update the existing Account")
        response, status = self.get_response(path=path, manifest=manifest)
        logger.info(f"Modified response: {response}, Status: {status}")
        expected = {
            "data": {
                "ready": True,
                "url": "http://testserver/api/v1/cli/apply/",
                "session_key": "841f08da12a1060d1fcd035094c96fe54dc666e30b97d5a6c99943200ff27217",
                "auth_header": "Token e667****",
                "api_token": "****8b35",
                "data": {
                    "apiVersion": "smarter.sh/v1",
                    "kind": "Account",
                    "metadata": {
                        "description": "TestAccount_AdminUser_b0ead1318ceae5be",
                        "name": "6031-2057-0556",
                        "version": "1.0.0",
                    },
                    "spec": {
                        "accountNumber": "6031-2057-0556",
                        "address1": "Avenida Reforma 222",
                        "address2": "Piso 19",
                        "city": "CDMX",
                        "companyName": "test data",
                        "country": "Mexico",
                        "currency": "MXN",
                        "isActive": True,
                        "isDefaultAccount": False,
                        "language": "es-ES",
                        "phoneNumber": "+1 617 834 6172",
                        "postalCode": "06600",
                        "state": "CDMX",
                        "timezone": "America/Mexico_City",
                    },
                },
                "chatbot_id": None,
                "chatbot_name": None,
                "is_smarter_api": True,
                "is_chatbot": False,
                "is_chatbot_smarter_api_url": False,
                "is_chatbot_named_url": False,
                "is_chatbot_sandbox_url": False,
                "is_chatbot_cli_api_url": False,
                "is_default_domain": False,
                "path": "/api/v1/cli/apply/",
                "root_domain": "testserver",
                "subdomain": "",
                "api_subdomain": None,
                "domain": "testserver",
                "timestamp": "2025-08-23T16:22:04.803599",
                "unique_client_string": "6031-2057-0556.http://testserver/api/v1/cli/apply/.user_agent.127.0.0.1.2025-08-23T16:22:04.803599",
                "client_key": "841f08da12a1060d1fcd035094c96fe54dc666e30b97d5a6c99943200ff27217",
                "ip_address": "127.0.0.1",
                "user_agent": "user_agent",
                "parsed_url": "ParseResult(scheme='http', netloc='testserver', path='/api/v1/cli/apply/', params='', query='', fragment='')",
                "request": True,
                "qualified_request": True,
                "url_path_parts": ["api", "v1", "cli", "apply"],
                "params": {},
                "uid": None,
                "cache_key": "c034ca0d717de16ce710620ac59813d06632f5cd11942af4f40bfc1a4880d4f8",
                "is_config": False,
                "is_dashboard": False,
                "is_workbench": False,
                "is_environment_root_domain": False,
                "account": {"accountNumber": "6031-2057-0556"},
                "user": {
                    "username": "test_admin_user_b0ead1318ceae5be",
                    "email": "test-admin-b0ead1318ceae5be@mail.com",
                },
                "user_profile": {
                    "user": {
                        "username": "test_admin_user_b0ead1318ceae5be",
                        "email": "test-admin-b0ead1318ceae5be@mail.com",
                    },
                    "account": {"accountNumber": "6031-2057-0556"},
                },
                "class_name": "SAMAccountBroker",
            },
            "message": "Account 6031-2057-0556 applied successfully",
            "api": "smarter.sh/v1",
            "thing": "Account",
            "metadata": {"command": "apply"},
        }

        self.assertEqual(status, HTTPStatus.OK.value)
        self.assertIsInstance(response, dict)

        # top level apply response
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        self.assertIn(SmarterJournalApiResponseKeys.MESSAGE, response.keys())
        self.assertIn(SmarterJournalApiResponseKeys.API, response.keys())
        self.assertIn(SmarterJournalApiResponseKeys.THING, response.keys())
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, response.keys())

        # validate the data that we just modified and applied
        spec = response[SmarterJournalApiResponseKeys.DATA]["data"]["spec"]
        for key, value in change_set.items():
            self.assertIn(key, spec)
            self.assertEqual(spec[key], value)

        logger.info("3.) re-query and validate that our changes are present when we call describe.")
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        response, status = self.get_response(path=path)
        logger.info(f"Re-queried response: {response}, Status: {status}")

        expected = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Account",
                "metadata": {
                    "name": "6031-2057-0556",
                    "description": "TestAccount_AdminUser_b0ead1318ceae5be",
                    "version": "1.0.0",
                },
                "spec": {
                    "config": {
                        "accountNumber": "6031-2057-0556",
                        "isDefaultAccount": False,
                        "companyName": "TestAccount_AdminUser_b0ead1318ceae5be",
                        "phoneNumber": "123-456-789",
                        "address1": None,
                        "address2": None,
                        "city": None,
                        "state": None,
                        "postalCode": None,
                        "country": "USA",
                        "language": "EN",
                        "timezone": None,
                        "currency": "USD",
                        "isActive": True,
                    }
                },
                "status": {
                    "created": "2025-08-23T16:22:03.853792+00:00",
                    "modified": "2025-08-23T16:22:03.853816+00:00",
                },
            },
            "message": "Account None described successfully",
            "api": "smarter.sh/v1",
            "thing": "Account",
            "metadata": {"command": "describe"},
        }

        self.assertEqual(status, HTTPStatus.OK.value)
        self.assertIsInstance(response, dict)

        # validate our changes
        data = response[SmarterJournalApiResponseKeys.DATA]
        config = data[SAMKeys.SPEC.value]["config"]
        self.assertEqual(config["companyName"], "test data")
        self.assertEqual(config["phoneNumber"], "+1 617 834 6172")
        self.assertEqual(config["address1"], "Avenida Reforma 222")
        self.assertEqual(config["address2"], "Piso 19")
        self.assertEqual(config["city"], "CDMX")
        self.assertEqual(config["state"], "CDMX")
        self.assertEqual(config["postalCode"], "06600")
        self.assertEqual(config["country"], "Mexico")
        self.assertEqual(config["language"], "es-ES")
        self.assertEqual(config["timezone"], "America/Mexico_City")
        self.assertEqual(config["currency"], "MXN")

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

        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK.value)
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
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.deploy, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED.value)
        self.assertIsInstance(response, dict)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertIn("not implemented", error["description"])

    def test_undeploy(self) -> None:
        """Test undeploy command"""
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.undeploy, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED.value)
        self.assertIsInstance(response, dict)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertIn("not implemented", error["description"])

    def test_logs(self) -> None:
        """Test logs command"""
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK.value)
        self.assertIsInstance(response, dict)

    def test_delete(self) -> None:
        """Test delete command"""
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        response, status = self.get_response(path=path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED)
        self.assertIsInstance(response, dict)

        error = response["error"]

        self.assertIn("description", error.keys())
        self.assertIn("errorClass", error.keys())
        self.assertIn("not implemented", error["description"])
