"""Test Api v1 CLI commands for account"""

import logging
from http import HTTPStatus
from urllib.parse import urlencode

import yaml
from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.api import SmarterApiVersions
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from .base_class import ApiV1CliTestBase

KIND = SAMKinds.ACCOUNT.value


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(f"{__name__}.TestApiCliV1Account")


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
        self.name = self.account.name
        self.query_params = urlencode({"name": self.name})
        logger.debug(
            "%s Setup test with kwargs: %s and query_params: %s",
            logger_prefix,
            json.dumps(self.kwargs),
            json.dumps(self.query_params),
        )

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
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
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
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        logger.info(f"base response: {response}, Status: {status}")
        expected = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Account",
                "metadata": {
                    "name": "test_account_admin_user_25aa3db5a9836253",
                    "description": "TestAccount_AdminUser_25aa3db5a9836253",
                    "version": "0.0.1",
                    "tags": ["test", "account", "mortal"],
                    "annotations": [
                        {"smarter.sh/created_by": "admin_user_factory"},
                        {"smarter.sh/purpose": "testing"},
                        {"smarter.sh/hash": "25aa3db5a9836253"},
                    ],
                    "accountNumber": "5390-0388-2767",
                },
                "spec": {
                    "config": {
                        "companyName": "TestAccount_AdminUser_25aa3db5a9836253",
                        "phoneNumber": "123-456-789",
                        "address1": "Smarter Way 4U",
                        "address2": "Suite 100",
                        "city": "Smarter",
                        "state": "WY",
                        "postalCode": "12345",
                        "country": "USA",
                        "language": "EN",
                        "timezone": "America/New_York",
                        "currency": "USD",
                    }
                },
                "status": {
                    "adminAccount": "5390-0388-2767",
                    "created": "2026-01-07T18:54:28.092Z",
                    "modified": "2026-01-07T18:54:28.092Z",
                },
            },
            "message": "Account test_account_admin_user_25aa3db5a9836253 described successfully",
            "api": "smarter.sh/v1",
            "thing": "Account",
            "metadata": {"key": "14e4a15ce216fd8d4f52eadcedc73665396fad044b44dc87cb139bc167e8dd20"},
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
        change_set["country"] = "MX"
        change_set["currency"] = "MXN"
        change_set["language"] = "es-ES"
        change_set["phoneNumber"] = "+1 617 834 6172"
        change_set["postalCode"] = "06600"
        change_set["state"] = "CDMX"
        change_set["timezone"] = "America/Mexico_City"
        data[SAMKeys.SPEC.value]["config"] = change_set

        # pop the status bc its read-only, if it exists
        # our expected outcome is that it does exist.
        if data.get(SAMKeys.STATUS.value):
            data.pop(SAMKeys.STATUS.value)
        else:
            logger.warning("Expected status to be present in the manifest data, but it was not found.")

        # convert the data back to yaml, since this is what the cli usually receives
        manifest = yaml.dump(data)
        logger.debug(f"Modified manifest to apply: {manifest}")
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.apply)

        logger.info("2.) apply the modified manifest to update the existing Account")
        response, status = self.get_response(path=path, manifest=manifest)
        logger.info(f"Modified response: {response}, Status: {status}")
        expected = {
            "data": {
                "account": {"accountNumber": "5829-4032-4255"},
                "api_subdomain": None,
                "api_token": "****6774",
                "auth_header": "Token 1ca4****",
                "cache_key": "6989b75d084613e55b779d27fcca7834ec4fb30ab53ff17ea3b701db39beb571",
                "chatbot_id": None,
                "chatbot_name": None,
                "class_name": "SAMAccountBroker",
                "data": {
                    "apiVersion": "smarter.sh/v1",
                    "kind": "Account",
                    "metadata": {
                        "accountNumber": "5829-4032-4255",
                        "annotations": [
                            {"smarter.sh/created_by": "admin_user_factory"},
                            {"smarter.sh/purpose": "testing"},
                            {"smarter.sh/hash": "7359552cbee2aade"},
                        ],
                        "description": "TestAccount_AdminUser_7359552cbee2aade",
                        "name": "test_account_admin_user_7359552cbee2aade",
                        "tags": ["test", "account", "mortal"],
                        "version": "0.0.1",
                    },
                    "spec": {
                        "config": {
                            "address1": "Avenida Reforma 222",
                            "address2": "Piso 19",
                            "city": "CDMX",
                            "companyName": "test data",
                            "country": "MX",
                            "currency": "MXN",
                            "language": "es-ES",
                            "phoneNumber": "+1 617 834 6172",
                            "postalCode": "06600",
                            "state": "CDMX",
                            "timezone": "America/Mexico_City",
                        }
                    },
                },
                "domain": "testserver",
                "ip_address": "127.0.0.1",
                "is_chatbot": False,
                "is_chatbot_cli_api_url": False,
                "is_chatbot_named_url": False,
                "is_chatbot_sandbox_url": False,
                "is_chatbot_smarter_api_url": False,
                "is_config": False,
                "is_dashboard": False,
                "is_default_domain": False,
                "is_environment_root_domain": False,
                "is_smarter_api": True,
                "is_workbench": False,
                "params": {},
                "parsed_url": "ParseResult(scheme='http', netloc='testserver', path='/api/v1/cli/apply/', params='', query='', fragment='')",
                "path": "/api/v1/cli/apply/",
                "qualified_request": True,
                "ready": True,
                "request": True,
                "root_domain": "testserver",
                "session_key": "7df6bc82d9cb2035a9a818b620a48ff68c8c08730e56a351d680f807243e921f",
                "subdomain": None,
                "timestamp": "2026-01-07T19:07:15.428214",
                "uid": None,
                "unique_client_string": "5829-4032-4255.http://testserver/api/v1/cli/apply/.user_agent.127.0.0.1.2026-01-07T19:07:15.428214",
                "url": "http://testserver/api/v1/cli/apply/",
                "url_original": "http://testserver/api/v1/cli/apply/",
                "url_path_parts": ["api", "v1", "cli", "apply"],
                "user": {
                    "username": "test_admin_user_7359552cbee2aade",
                    "email": "test-admin-7359552cbee2aade@mail.com",
                },
                "user_agent": "user_agent",
                "user_profile": {
                    "user": {
                        "username": "test_admin_user_7359552cbee2aade",
                        "email": "test-admin-7359552cbee2aade@mail.com",
                    },
                    "account": {"accountNumber": "5829-4032-4255"},
                },
            },
            "message": "Account test_account_admin_user_7359552cbee2aade applied successfully",
            "api": "smarter.sh/v1",
            "thing": "Account",
            "metadata": {"key": "74aff0e7277d1552c32ef89b6f0d5413e1d864068f3ba786117dd5962609faf2"},
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
        spec = response[SmarterJournalApiResponseKeys.DATA]["data"]["spec"]["config"]
        for key, value in change_set.items():
            self.assertIn(key, spec)
            self.assertEqual(spec[key], value)

        logger.info("3.) re-query and validate that our changes are present when we call describe.")
        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        logger.info(f"Re-queried response: {response}, Status: {status}")

        expected = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Account",
                "metadata": {
                    "name": "test_account_admin_user_02a6745418b64990",
                    "description": "test data",
                    "version": "0.0.1",
                    "tags": ["test", "account", "mortal"],
                    "annotations": [
                        {"smarter.sh/created_by": "admin_user_factory"},
                        {"smarter.sh/purpose": "testing"},
                        {"smarter.sh/hash": "02a6745418b64990"},
                    ],
                    "accountNumber": "7872-3063-5091",
                },
                "spec": {
                    "config": {
                        "companyName": "test data",
                        "phoneNumber": "+1 617 834 6172",
                        "address1": "Avenida Reforma 222",
                        "address2": "Piso 19",
                        "city": "CDMX",
                        "state": "CDMX",
                        "postalCode": "06600",
                        "country": "MX",
                        "language": "es-ES",
                        "timezone": "America/Mexico_City",
                        "currency": "MXN",
                    }
                },
                "status": {
                    "adminAccount": "7872-3063-5091",
                    "created": "2026-01-07T19:17:14.723Z",
                    "modified": "2026-01-07T19:17:15.582Z",
                },
            },
            "message": "Account test_account_admin_user_02a6745418b64990 described successfully",
            "api": "smarter.sh/v1",
            "thing": "Account",
            "metadata": {"key": "1770a3d88ee83425030c484fc3e0e5f2a19d01a71a798225e725596efe0ae79b"},
        }

        self.assertEqual(status, HTTPStatus.OK.value)
        self.assertIsInstance(response, dict)

        # validate our changes
        data = response[SmarterJournalApiResponseKeys.DATA]
        config = data[SAMKeys.SPEC.value]["config"]
        self.assertEqual(
            config["companyName"], "test data", f"companyName did not persist correctly in apply: {config}"
        )
        self.assertEqual(
            config["phoneNumber"], "+1 617 834 6172", f"phoneNumber did not persist correctly in apply: {config}"
        )
        self.assertEqual(
            config["address1"], "Avenida Reforma 222", f"address1 did not persist correctly in apply: {config}"
        )
        self.assertEqual(config["address2"], "Piso 19", f"address2 did not persist correctly in apply: {config}")
        self.assertEqual(config["city"], "CDMX", f"city did not persist correctly in apply: {config}")
        self.assertEqual(config["state"], "CDMX", f"state did not persist correctly in apply: {config}")
        self.assertEqual(config["postalCode"], "06600", f"postalCode did not persist correctly in apply: {config}")
        self.assertEqual(config["country"], "MX", f"country did not persist correctly in apply: {config}")
        self.assertEqual(config["language"], "es-ES", f"language did not persist correctly in apply: {config}")
        self.assertEqual(
            config["timezone"], "America/Mexico_City", f"timezone did not persist correctly in apply: {config}"
        )
        self.assertEqual(config["currency"], "MXN", f"currency did not persist correctly in apply: {config}")

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
                    logger.error(f"Item is not a dict: {item} {type(item)}")
                    return False
                if set(item.keys()) != title_names:
                    logger.error(f"Item keys do not match title names: {item.keys()} vs {title_names}")
                    return False

            return True

        path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.get, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)

        expected = {
            "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "Account",
                "name": "2868-0693-2944",
                "metadata": {"count": 1},
                "kwargs": {"kwargs": {}},
                "data": {
                    "titles": [
                        {"name": "accountNumber", "type": "CharField"},
                        {"name": "companyName", "type": "CharField"},
                        {"name": "createdAt", "type": "DateTimeField"},
                        {"name": "updatedAt", "type": "DateTimeField"},
                    ],
                    "items": [
                        {
                            "accountNumber": "2868-0693-2944",
                            "companyName": "test data",
                            "createdAt": "2026-01-07T19:40:31.448806Z",
                            "updatedAt": "2026-01-07T19:40:32.124334Z",
                        }
                    ],
                },
            },
            "message": "Accounts got successfully",
            "api": "smarter.sh/v1",
            "thing": "Account",
            "metadata": {"key": "04fc1fb0e4a156f2986e7e776027e090ba1f8a9c92bf570c6124f21c8768008d"},
        }

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
